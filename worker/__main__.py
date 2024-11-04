import asyncio
import io
import subprocess
import tarfile
from os import getenv
from pathlib import Path
from textwrap import dedent
from typing import Optional

import httpx
import typer
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from nearai.delegation import OnBehalfOf
from nearai.jobs import JobsApi
from nearai.lib import parse_location
from nearai.registry import registry
from openapi_client.models.entry_location import EntryLocation
from pydantic import BaseModel
from shared.auth_data import AuthData

app = typer.Typer()
loop = asyncio.get_event_loop()

WORKER_PORT = int(getenv("WORKER_PORT"))
WORKER_SLEEP_TIME = int(getenv("WORKER_SLEEP_TIME", 1))
WORKER_URL = getenv("WORKER_URL", f"http://worker:{WORKER_PORT}")
WORKER_JOB_TIMEOUT = int(getenv("WORKER_JOB_TIMEOUT", 60 * 60 * 6))  # 6 hours
WORKER_ACCOUNT_ID = getenv("WORKER_ACCOUNT_ID", "nearaiworker.near")
WORKER_SIGNATURE = getenv("WORKER_SIGNATURE")
JOB_DIR = Path("~/job/")

JOBS_API = JobsApi()


class SetupParams(BaseModel):
    auth_data: AuthData
    on_behalf_of: str


def try_parse_location(location: str) -> Optional[EntryLocation]:
    try:
        return parse_location(location)
    except Exception:
        return None


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
                if not job.registry_path:
                    # TODO: fail the job with null path err
                    continue
                location = try_parse_location(job.registry_path)
                if not location:
                    # TODO: fail the job with parse err
                    continue

                ## 3. Download the job
                with OnBehalfOf(client, job.selected.account_id):
                    downloaded = registry.download(job.registry_path)

                    ## tar directory in mem and send over
                    tar_file = io.BytesIO()
                    with tarfile.open(fileobj=tar_file, mode="w") as tar:
                        tar.add(downloaded)
                    tar_file.seek(0)

                ## 4. Setup the worker
                setup_params = SetupParams(
                    auth_data=AuthData(
                        account_id=WORKER_ACCOUNT_ID,
                        public_key=WORKER_PUBKEY,
                        signature=WORKER_SIGNATURE,
                    ),
                    on_behalf_of=job.selected.account_id,
                )
                await client.post(WORKER_URL + "/setup", data=setup_params.model_dump_json())

                ## 5. Execute the job
                response = await client.post(WORKER_URL + "/execute", files={"file": ("main.tar", tar_file)})

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
    def setup(setup_params: SetupParams):
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
