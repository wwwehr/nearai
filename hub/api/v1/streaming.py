import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Delta, Message, Thread, get_session

# Create a websocket endpoint that takes a checkpoint_id as a parameter and receives Delta messages.
# Store deltas in memory by checkpoint_id.
# Accept an Event (command) called NewCheckpoint. When a NewCheckpoint command is received, save all the Deltas since the last checkpoint into the new environment.

streaming_router = APIRouter()
logger = logging.getLogger(__name__)

# create a thread safe registry of open subscriptions
subscriptions = {}


def check_thread_access(thread: Thread, auth: AuthToken) -> bool:
    """Check if the authenticated user has access to the thread.

    :param thread: The thread to check access for
    :param auth: The authentication token of the user
    :return: True if the user has access, False otherwise
    """
    if thread.account_id == auth.account_id:
        return True

    # Check if the thread has been shared with the user
    # This assumes there's a 'shared_with' field in the Thread model
    # You may need to adjust this based on your actual data model
    if hasattr(thread, "shared_with") and auth.user_id in thread.shared_with:
        return True

    return False


# @app.websocket("/ws-subscribe")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         await websocket.send_text(f"Message text was: {data}")
#
#
# Create a server-sent events endpoint that streams deltas.
@streaming_router.get("/threads/{thread_id}/subscribe")
async def thread_subscribe(thread_id: str, message_id: Optional[str] = None, auth: AuthToken = Depends(revokable_auth)):
    # fetch thread
    with get_session() as session:
        thread = session.get(Thread, thread_id)
        # check thread permissions

        if not check_thread_access(thread, auth):
            raise HTTPException(status_code=403, detail="Access to thread denied")
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        subscriptions[thread_id] = {}
    # fetch messages
    # if there is a later message_id than was requested, stream messages
    # stream deltas

    return StreamingResponse(test_generator(), media_type="text/event-stream")


@streaming_router.post("/threads/{thread_id}/messages/{message_id}/deltas")
async def create_delta(
    thread_id: str,
    message_id: str,
    delta: Delta = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> None:
    with get_session() as session:
        message_model = session.get(Message, message_id)
        if message_model is None:
            logging.error(f"Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")

        # create delta
        delta = Delta(
            id=delta.id,
            content=delta.content,
            filename=delta.filename,
        )
        logger.info(f"Creating delta: {delta}")
        session.add(delta)
        session.commit()
