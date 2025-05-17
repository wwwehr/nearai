import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from os import getenv
from typing import Callable, List, Union

from dotenv import load_dotenv
from nearai.shared.client_config import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from secretvaults import OperationType, SecretVaultWrapper

from hub.api.v1.models import Delta, get_session

load_dotenv()

logger = logging.getLogger(__name__)


def resolve_nillion_host_from_did(did: str) -> dict[str, str]:
    host_map = {
        "did:nil:testnet:nillion15lcjxgafgvs40rypvqu73gfvx6pkx7ugdja50d": "https://1.nildb.wehrenterprises.org",
        "did:nil:testnet:nillion1dfh44cs4h2zek5vhzxkfvd9w28s5q5cdepdvml": "https://2.nildb.wehrenterprises.org",
        "did:nil:testnet:nillion19t0gefm7pr6xjkq2sj40f0rs7wznldgfg4guue": "https://3.nildb.wehrenterprises.org",
    }
    if did in host_map:
        return {"did": did, "url": host_map[did]}
    else:
        raise ValidationError("failed to map Nillion host")


def run_async_in_sync(coro):
    """Run async code from sync context and BLOCK until complete."""
    try:
        # Try asyncio.run first (works if no event loop exists)
        return asyncio.run(coro)
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # We're in an existing event loop, use a thread and WAIT
            def run_in_new_loop():
                # Create completely isolated event loop
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # Run the coroutine and return the result
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            # Create thread and BLOCK until it completes
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                result = future.result()  # 👈 THIS BLOCKS until thread is done
                return result
        else:
            raise


class Provider(Enum):
    HYPERBOLIC = "hyperbolic"
    FIREWORKS = "fireworks"
    LOCAL = "local"


async def handle_stream(
    thread_id, run_id, message_id, resp_stream, add_usage_callback: Callable
):
    response_chunks = []
    deltas_to_commit = []
    commit_every = 5  # Commit every N chunks to reduce DB overhead
    is_first_chunk = True

    if run_id is not None:
        with get_session() as session:
            for _idx, chunk in enumerate(resp_stream):
                c = json.dumps(chunk.model_dump())
                response_chunks.append(c)

                txt = chunk.choices[0].delta.content
                if txt is not None:
                    content = {
                        "content": [
                            {"index": 0, "type": "text", "text": {"value": txt}}
                        ]
                    }
                    delta = Delta(
                        event="thread.message.delta",
                        content=content,
                        created_at=datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S.%f"
                        )[:-3],
                        run_id=run_id,
                        thread_id=thread_id,
                        message_id=message_id,
                    )
                    deltas_to_commit.append(delta)

                    # Commit in batches to reduce DB overhead but commit the first chunk for responsiveness
                    if is_first_chunk or len(deltas_to_commit) >= commit_every:
                        is_first_chunk = False
                        session.add_all(deltas_to_commit)
                        session.commit()
                        deltas_to_commit = []

                # Yield immediately and let the event loop process
                yield f"data: {c}\n\n"
                await asyncio.sleep(0)

            completion_delta = Delta(
                object="thread.message.completed",
                content="",
                created_at=datetime.now(timezone.utc),
                run_id=run_id,
                thread_id=thread_id,
                message_id=message_id,
            )
            deltas_to_commit.append(completion_delta)
            session.add_all(deltas_to_commit)
            session.commit()

    else:
        for chunk in resp_stream:
            c = json.dumps(chunk.model_dump())
            response_chunks.append(c)
            yield f"data: {c}\n\n"
            await asyncio.sleep(
                0
            )  # lets the event loop yield, otherwise it batches yields

    yield "data: [DONE]\n\n"
    full_response_text = "".join(response_chunks)
    add_usage_callback(full_response_text)


def get_llm_ai(provider: str) -> OpenAI:
    if provider == "hyperbolic":
        return OpenAI(
            base_url="https://api.hyperbolic.xyz/v1",
            api_key=getenv("HYPERBOLIC_API_KEY"),
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    elif provider == "fireworks":
        return OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=getenv("FIREWORKS_API_KEY"),
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    elif provider == "local":
        return OpenAI(
            base_url=getenv("PROVIDER_LOCAL_BASE_URL"),
            api_key=getenv("PROVIDER_LOCAL_API_KEY"),
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    else:
        raise NotImplementedError


class SecretMessage(BaseModel):
    """A Nillion secret message."""

    id: str = Field(alias="_id")
    hosts: List[str]


class Message(BaseModel):
    """A chat message."""

    role: str
    content: Union[SecretMessage, List, str]

    @field_validator("content", mode="before")
    @classmethod
    def ensure_string_content(cls, v):
        """Ensure content within the messages is always a string."""
        if v is None:
            return ""

        # Iterate recursively over the object, converting values to str
        if isinstance(v, list):
            return [cls.ensure_string_content(i) for i in v]
        elif isinstance(v, dict):
            return {k: cls.ensure_string_content(v) for k, v in v.items()}
        else:
            return str(v)

    @model_validator(mode="after")
    def process_content(self) -> "Message":
        """Detect a Nillion message and decode."""
        if not isinstance(self.content, str):
            return self

        logger.info(
            "NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW NPW"
        )

        async def async_decode():
            try:
                logger.info("|   running async_decode")
                nillion_secret_info = SecretMessage.model_validate_json(
                    str(self.content)
                )
                logger.info(f"|   Valid JSON matching {SecretMessage.__name__} schema!")
                logger.info(f"|   {self.content}")
                node_config = [
                    resolve_nillion_host_from_did(x) for x in nillion_secret_info.hosts
                ]
                creds = {
                    "secret_key": getenv("NILLION_ORG_SECRET_KEY"),
                    "org_did": getenv("NILLION_ORG_ID"),
                }
                # logger.info(f"|   nodes: {node_config}")
                # logger.info(f"|   creds: {creds}")
                collection = SecretVaultWrapper(
                    node_config,
                    creds,
                    getenv("NILLION_SCHEMA_ID"),
                    operation=OperationType.STORE,
                )
                logger.info("|>  collection.init()")
                await collection.init()
                logger.info("|<  collection.init()")
                logger.info("|>  collection.read_from_nodes()")
                data_read = await collection.read_from_nodes(
                    {"_id": nillion_secret_info.id}
                )
                logger.info("|<  collection.read_from_nodes()")
                if isinstance(data_read, list):
                    logger.info(f"|   is list {json.dumps(data_read, indent=2)}")
                    return str(data_read[0]["message"])
                else:
                    logger.info(f"|   is unknown: {data_read.__class__}")
                    return str(data_read)
            except (ValidationError, json.JSONDecodeError):
                logger.info(f"!   DOES NOT match {SecretMessage.__name__} schema!")
                return self.content
            except Exception as e:
                logger.info(f"!   failed to reconstruct nillion data {e}")
                raise

        logger.info(">>> NPW starting async_decode")
        transformed_content = run_async_in_sync(async_decode())
        logger.info(f"!   collection records: {transformed_content}")
        logger.info("<<< NPW done")
        return self.model_copy(update={'content': transformed_content})
