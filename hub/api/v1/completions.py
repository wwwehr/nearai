from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import json
from typing import Callable
from enum import Enum

from os import getenv
load_dotenv()


class Provider(Enum):
    HYPERBOLIC = "hyperbolic"
    FIREWORKS = "fireworks"


def handle_stream(resp_stream, add_usage_callback: Callable):
    response_chunks = []

    for chunk in resp_stream:
        c = json.dumps(chunk.model_dump())
        response_chunks.append(c)
        print(c)
        yield f"data: {c}\n\n"

    yield "data: [DONE]\n\n"
    full_response_text = ''.join(response_chunks)

    add_usage_callback(full_response_text)


def get_llm_ai(provider: str) -> OpenAI:
    if provider == "hyperbolic":
        return OpenAI(base_url="https://api.hyperbolic.xyz/v1", api_key=getenv("HYPERBOLIC_API_KEY"))
    elif provider == "fireworks":
        return OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=getenv("FIREWORKS_API_KEY"))
    else:
        raise NotImplementedError


class Message(BaseModel):
    role: str
    content: str
