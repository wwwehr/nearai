from typing import Any, Callable

from openai import OpenAI
from openai.types.chat import ChatCompletion

from .config import CONFIG


def create_completion_fn(model: str) -> Callable[..., ChatCompletion]:
    client = OpenAI(base_url=CONFIG.inference_url, api_key=CONFIG.inference_api_key)

    def complete(**kwargs: Any) -> ChatCompletion:
        completion: ChatCompletion = client.chat.completions.create(model=model, **kwargs)
        return completion

    return complete