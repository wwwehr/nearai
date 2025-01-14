import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.models import RunSchedule, get_session
from hub.api.v1.models import Thread as ThreadModel

schedule_run_router = APIRouter(tags=["Run Schedule"])

logger = logging.getLogger(__name__)


class CreateScheduleRunRequest(BaseModel):
    """Request model for creating a new scheduled run."""

    agent: str
    input_message: str
    run_params: Dict[str, str]
    thread_id: Optional[str]
    run_at: datetime


@schedule_run_router.post("/schedule_run")
def schedule_run(
    request: CreateScheduleRunRequest,
    auth: AuthToken = Depends(get_auth),
):
    logger.info(f"Creating scheduled run for agent {request.run_at}: {datetime.now()}")
    assert request.run_at > datetime.now(), "run_at should be in the future"

    with get_session() as session:
        # TODO add permission check for user to avoid many scheduled runs

        # agent name validation
        if EntryLocation.from_str(request.agent) is None:
            raise HTTPException(status_code=400, detail="Agent name is invalid")

        if request.thread_id is not None:
            # verify given thread_id
            thread_model = session.get(ThreadModel, request.thread_id)
            if thread_model is None:
                raise HTTPException(status_code=404, detail="Thread not found")
            if thread_model.owner_id != auth.account_id:
                raise HTTPException(status_code=403, detail="You don't have permission to access this thread")

        run = RunSchedule(
            agent=request.agent,
            input_message=request.input_message,
            thread_id=request.thread_id,
            run_params=request.run_params,
            run_at=request.run_at,
            created_by=auth.account_id,
        )
        session.add(run)
        session.commit()

        logger.info(f"Scheduled run id {run.id} for agent {request.agent} has been created")
