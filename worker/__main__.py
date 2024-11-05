import asyncio
import datetime
import os
import signal
import subprocess
import tarfile
from datetime import timedelta
from os import getenv
from pathlib import Path
from typing import Optional

import httpx
import typer
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from nearai.delegation import OnBehalfOf
from nearai.jobs import JobsApi
from nearai.lib import parse_location
from nearai.registry import registry
from nearai.config import CONFIG, Config, save_config_file
from openapi_client.api.delegation_api import DelegationApi
from openapi_client.models.entry_location import EntryLocation
from openapi_client.models.job_status import JobStatus
from openapi_client.models.jobs import Jobs
from pydantic import BaseModel
from shared.auth_data import AuthData

app = typer.Typer()
loop = asyncio.get_event_loop()

WORKER_PORT = int(getenv("WORKER_PORT"))
WORKER_SLEEP_TIME = int(getenv("WORKER_SLEEP_TIME", 1))
WORKER_URL = getenv("WORKER_URL", f"http://worker:{WORKER_PORT}")
WORKER_JOB_TIMEOUT = int(getenv("WORKER_JOB_TIMEOUT", 60 * 60 * 6))  # 6 hours
WORKER_ACCOUNT_ID = getenv("NEARAIWORKER_ACCOUNT_ID", "nearaiworker.near")
WORKER_SIGNATURE = getenv("NEARAIWORKER_SIGNATURE")

JOB_DIR = Path("~/job/")
JOBS_API = JobsApi()
DELEGATION_API = DelegationApi()

SCHEDULER_ACCOUNT_ID = getenv("NEARAISCHEDULER_ACCOUNT_ID", "nearaischeduler.near")


class SetupParams(BaseModel):
    auth_data: AuthData
    on_behalf_of: str


class ResultJson(BaseModel):
    output: str


class JobResult(BaseModel):
    stdout: str
    stderr: str
    return_code: int


def try_parse_location(location: str) -> Optional[EntryLocation]:
    try:
        return parse_location(location)
    except Exception:
        return None


async def run_scheduler():
    DELEGATION_API.delegate_v1_delegation_delegate_post(
        delegate_account_id=WORKER_ACCOUNT_ID,
        expires_at=datetime.datetime.now() + timedelta(days=1),
    )
    while True:
        try:
            await asyncio.sleep(WORKER_SLEEP_TIME)
            async with httpx.AsyncClient() as client:
                ## Poll worker health
                response = await client.get(WORKER_URL + "/health")
                if response.status_code != 200:
                    print(f"Worker is not healthy ... retrying")
                    continue

                ## Get pending jobs
                selected_job = JOBS_API.get_pending_job_v1_jobs_get_pending_job_post(
                    worker_id=SCHEDULER_ACCOUNT_ID,
                )
                if not selected_job:
                    print(f"No pending jobs ... retrying")
                    continue

                ## Get the first job
                ## ensure it's not already running
                if not selected_job.selected:
                    print(f"Job is not selected ... retrying")
                    continue
                if not selected_job.registry_path:
                    # TODO: fail the job with null path err
                    print(f"Job has no registry path ... retrying")
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output="No registry path").model_dump_json(),
                    )
                    continue
                location = try_parse_location(selected_job.registry_path)
                if not location:
                    # TODO: fail the job with parse err
                    print(f"Failed to parse registry path: {selected_job.registry_path} ... retrying")
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output="Failed to parse registry path").model_dump_json(),
                    )
                    continue

                ## 3. Download the job
                try:
                    ## Delegate to the worker as the user
                    with OnBehalfOf(client, selected_job.job.account_id):
                        DELEGATION_API.delegate_v1_delegation_delegate_post(
                            delegate_account_id=WORKER_ACCOUNT_ID,
                            expires_at=datetime.datetime.now() + timedelta(days=1),
                        )
                        downloaded = registry.download(location)
                except Exception as e:
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        reason=str(e),
                    )
                    with OnBehalfOf(client, selected_job.job.account_id):
                        DELEGATION_API.revoke_delegation_v1_delegation_revoke_delegation_post(
                            delegate_account_id=WORKER_ACCOUNT_ID
                        )
                    print(f"Failed to download job ... retrying")
                    continue

                ## 5. Execute the job
                success = False
                try:
                    response = await client.post(
                        WORKER_URL + "/execute",
                        files={
                            "file": ("main.tar", downloaded),
                            "job": selected_job.model_dump_json(),
                        },
                        timeout=WORKER_JOB_TIMEOUT,
                    )
                    if response.status_code != 200:
                        raise Exception(response.text)

                    success = True
                    response_json = response.json()
                    job_result = JobResult(**response_json)
                except Exception as e:
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output=f"Failed to execute job: {e}").model_dump_json(),
                    )
                    print(f"Failed to execute job ... retrying")

                ## 6. cleanup
                if success:
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output=job_result.model_dump_json()).model_dump_json(),
                    )
            
                ## Revoke access of the worker from the scheduler
                try:
                    with OnBehalfOf(client, selected_job.job.account_id):
                        DELEGATION_API.revoke_delegation_v1_delegation_revoke_delegation_post(
                            delegate_account_id=WORKER_ACCOUNT_ID
                        )
                        DELEGATION_API.revoke_delegation_v1_delegation_revoke_delegation_post(
                            delegate_account_id=SCHEDULER_ACCOUNT_ID
                        )
                except Exception as e:
                    continue

                ## kill the worker
                try:
                    result = await client.post(WORKER_URL + "/reset")
                    # --- unreachable ---
                except Exception as e:
                    print(f"Error: {e}")
        except Exception as e:
            print(f"Error: {e}")


def run_worker():
    app = FastAPI()
    current_job = None

    @app.post("/reset")
    def reset():
        os.kill(os.getpid(), signal.SIGTERM)

    @app.get("/health")
    async def health():
        return "OK"

    @app.get("/current_job")
    async def get_current_job() -> Optional[Jobs]:
        return current_job

    @app.post("/execute")
    def execute(job: Jobs, file: UploadFile = File(...)) -> JobResult:
        if not file.filename.endswith(".tar"):
            raise HTTPException(status_code=500, detail="The uploaded file is not a tar file.")

        if len(file.filename) > 256:
            raise HTTPException(status_code=500, detail="The filename is too long. It must be 256 characters or less.")
    
        ## Update auth
        CONFIG.auth.on_behalf_of = job.account_id
        save_config_file(CONFIG.model_dump())

        ## save current job
        current_job = job  # noqa: F841

        JOB_DIR.mkdir(parents=True, exist_ok=True)
        file_location = JOB_DIR / file.filename
        file_location.write_bytes(file.read())

        try:
            # untar the file into the job directory
            with tarfile.open(file_location, "r") as tar:
                tar.extractall(JOB_DIR)
            file_location.unlink()

            # Execute the run.sh script in a subprocess
            result = subprocess.run(
                ["bash", str(JOB_DIR / "run.sh")],
                capture_output=True,
                text=True,
                timeout=WORKER_JOB_TIMEOUT,
            )

            ## cleanup
            current_job = None  # noqa: F841
            return JobResult(stdout=result.stdout, stderr=result.stderr, return_code=result.returncode)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Execution timed out.")  # noqa: B904


    uvicorn.run(app, host="0.0.0.0", port=WORKER_PORT)


@app.command()
def scheduler():
    loop.run_until_complete(run_scheduler())


@app.command()
def worker():
    run_worker()


if __name__ == "__main__":
    app()
