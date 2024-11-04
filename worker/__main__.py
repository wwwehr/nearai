import asyncio
import io
import subprocess
from os import getenv
from pathlib import Path
from textwrap import dedent

import httpx
import typer
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from nearai.delegation import OnBehalfOf
from nearai.jobs import JobsApi
from pydantic import BaseModel, field_serializer

app = typer.Typer()
loop = asyncio.get_event_loop()

WORKER_PORT = int(getenv("WORKER_PORT"))
WORKER_SLEEP_TIME = int(getenv("WORKER_SLEEP_TIME", 1))
WORKER_URL = getenv("WORKER_URL", f"http://worker:{WORKER_PORT}")
WORKER_JOB_TIMEOUT = int(getenv("WORKER_JOB_TIMEOUT", 60 * 60 * 6))  # 6 hours
JOB_DIR = Path("~/job/")

JOBS_API = JobsApi()


class SetupParams(BaseModel):
    pass


class A(BaseModel):
    a: int
    b: str
    c: str

    @field_serializer("c")
    def format_c(self, value: str) -> str:
        return "test"


my_thing = A(a=1, b="2", c="three")
print(my_thing.model_dump())


async def run_scheduler():
    while True:
        try:
            await asyncio.sleep(WORKER_SLEEP_TIME)
            async with httpx.AsyncClient() as client:
                ## 1. Poll worker health
                response = await client.get(WORKER_URL + "/health")
                if response.status_code != 200:
                    continue

                ## 2. Poll job
                job = JOBS_API.get_pending_job_v1_jobs_get_pending_job_post(
                    worker_id="123",
                )
                if not job.selected:
                    continue

                with OnBehalfOf(client, job.selected.delegation_id):
                    pass

                python_code = dedent("""
                import os
                print(os.environ)
                print(os.listdir("."))
                ## curl google.com
                import httpx
                response = httpx.get("https://google.com")
                print(response.text)
                """)

                ## bytesio file
                tmp_file = io.BytesIO()
                tmp_file.write(python_code.encode("utf-8"))
                tmp_file.seek(0)

                ## send request
                response = await client.post(WORKER_URL + "/execute", files={"file": ("main.py", tmp_file)})
                print(response.json())
        except Exception as e:
            print(e)


def run_worker():
    app = FastAPI()

    @app.get("/health")
    def health():
        return "OK"

    @app.post("/setup")
    def setup(file: UploadFile = File(...)):
        pass

    @app.post("/execute")
    async def execute(file: UploadFile = File(...)):
        if not file.filename.endswith(".py"):
            raise HTTPException(status_code=500, detail="The uploaded file is not a Python file.")

        if len(file.filename) > 256:
            raise HTTPException(status_code=500, detail="The filename is too long. It must be 256 characters or less.")

        JOB_DIR.mkdir(parents=True, exist_ok=True)
        file_location = JOB_DIR / file.filename
        file_location.write_bytes(await file.read())

        try:
            # Execute the file in a subprocess
            result = subprocess.run(
                ["python", file_location],
                capture_output=True,
                text=True,
                timeout=WORKER_JOB_TIMEOUT,
            )

            # Return the output or error
            if result.returncode == 0:
                return {"output": result.stdout}
            else:
                raise HTTPException(status_code=500, detail=result.stderr)

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Execution timed out.")  # noqa: B904

        finally:
            # Clean up the temporary file
            import os

            os.remove(file_location)

    uvicorn.run(app, host="0.0.0.0", port=WORKER_PORT)


@app.command()
def scheduler():
    loop.run_until_complete(run_scheduler())


@app.command()
def worker():
    run_worker()


if __name__ == "__main__":
    app()
