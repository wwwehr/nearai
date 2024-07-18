from pydantic import BaseModel
from typing import Optional, Union, List, Dict
from api.v1.sql import SqlClient
from api.v1.completions import get_llm_ai, Message, handle_stream, Provider
from api.v1.auth import get_current_user, AuthToken

import logging
import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.responses import StreamingResponse

v1_router = APIRouter()
db = SqlClient()
logger = logging.getLogger(__name__)
security = HTTPBearer()


class ResponseFormat(BaseModel):
    """The format of the response."""
    type: str
    """The type of the response format."""
    json_schema: Optional[Dict] = None
    """Optional JSON schema for the response format."""


class LlmRequest(BaseModel):
    """Base class for LLM requests."""
    model: str = "accounts/fireworks/models/mixtral-8x22b-instruct"
    """The model to use for generation."""
    provider: str = "fireworks"
    """The provider to use for generation."""
    max_tokens: Optional[int] = 1024
    """The maximum number of tokens to generate."""
    logprobs: Optional[int] = None
    """The log probabilities of the generated tokens."""
    temperature: float = 1.0
    """The temperature for sampling."""
    top_p: float = 1.0
    """The top-p value for nucleus sampling."""
    frequency_penalty: Optional[float] = 0.0
    """The frequency penalty."""
    n: int = 1
    """The number of completions to generate."""
    stop: Optional[Union[str, List[str]]] = None
    """The stop sequence(s) for generation."""
    response_format: Optional[ResponseFormat] = None
    """The format of the response."""
    stream: bool = False
    """Whether to stream the response."""


class CompletionsRequest(LlmRequest):
    """Request for completions."""
    prompt: str


class ChatCompletionsRequest(LlmRequest):
    """Request for chat completions."""
    messages: List[Message]


@v1_router.post("/completions")
def completions(request: CompletionsRequest, auth: AuthToken = Depends(get_current_user)):
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid token")
    logger.info(f"Received completions request: {request.model_dump()}")

    llm = get_llm_ai(request.provider)

    resp = llm.completions.create(
        **request.model_dump(exclude={"provider", "response_format"}))

    if request.stream:
        def add_usage_callback(response_text):
            logger.info(f"Stream done, adding usage to database")
            db.add_user_usage(auth.account_id, request.prompt, response_text,
                              request.model, request.provider, "/completions")

        return StreamingResponse(handle_stream(resp, add_usage_callback), media_type="text/event-stream")
    else:
        c = json.dumps(resp.model_dump())

        db.add_user_usage(
            auth.account_id, request.prompt, c, request.model, request.provider, "/completions")

        return JSONResponse(content=json.loads(c))


@v1_router.post("/chat/completions")
async def chat_completions(request: ChatCompletionsRequest, auth: AuthToken = Depends(get_current_user)):
    logger.info(f"Received chat completions request: {request.model_dump()}")

    llm = get_llm_ai(request.provider)

    resp = llm.chat.completions.create(
        **request.model_dump(exclude={"provider"}))

    if request.stream:
        def add_usage_callback(response_text):
            logger.info(f"Stream done, adding usage to database")
            db.add_user_usage(auth.account_id, json.dumps([x.model_dump() for x in request.messages]), response_text,
                              request.model, request.provider, "/chat/completions")

        return StreamingResponse(handle_stream(resp, add_usage_callback), media_type="text/event-stream")

    else:
        c = json.dumps(resp.model_dump())
        db.add_user_usage(
            auth.account_id, json.dumps([x.model_dump() for x in request.messages]), c, request.model, request.provider, "/chat/completions")

        return JSONResponse(content=json.loads(c))


@v1_router.get("/models")
async def get_models():
    # TODO: merge all models from all providers.
    for p in Provider:
        try:
            m = get_llm_ai(p.value).models.list()
            return JSONResponse(content=m.model_dump())
        except Exception as e:
            logger.error(f"Error getting models from provider {p.value}: {e}")
