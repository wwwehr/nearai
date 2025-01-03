import io
from typing import Any, Dict, Iterable, List, Literal, Optional, Union

import litellm
import openai
import requests
from litellm import CustomStreamWrapper, ModelResponse
from litellm import completion as litellm_completion
from litellm.types.completion import ChatCompletionMessageParam
from openai import NOT_GIVEN, NotGiven
from openai.types.beta.thread import Thread
from openai.types.beta.vector_store import VectorStore
from openai.types.beta.vector_stores import VectorStoreFile
from openai.types.file_object import FileObject

from nearai.shared.client_config import DEFAULT_MODEL_MAX_TOKENS, DEFAULT_MODEL_TEMPERATURE, ClientConfig
from nearai.shared.models import (
    AutoFileChunkingStrategyParam,
    ChunkingStrategy,
    ExpiresAfter,
    GitHubSource,
    GitLabSource,
    SimilaritySearch,
    SimilaritySearchFile,
    StaticFileChunkingStrategyParam,
)
from nearai.shared.provider_models import ProviderModels


class InferenceClient(object):
    def __init__(self, config: ClientConfig) -> None:  # noqa: D107
        self._config = config

        private_auth = config.auth.generate_bearer_token() if config.auth is not None else None
        private_client = openai.OpenAI(base_url=self._config.base_url, api_key=private_auth)

        def completions(
            model: str,
            messages: Iterable[ChatCompletionMessageParam],
            stream: bool = False,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            **kwargs: Any,
        ) -> Union[ModelResponse, CustomStreamWrapper]:
            """Takes a `model` and `messages` and returns completions.

            `model` can be:
            1. full path `provider::model_full_path`.
            2. `model_short_name`. Default provider will be used.
            """
            provider, model = self.provider_models.match_provider_model(model)

            if temperature is None:
                temperature = DEFAULT_MODEL_TEMPERATURE

            if max_tokens is None:
                max_tokens = DEFAULT_MODEL_MAX_TOKENS

            # NOTE(#246): this is to disable "Provider List" messages.
            litellm.suppress_debug_info = True

            for i in range(0, self._config.num_inference_retries):
                try:
                    result: Union[ModelResponse, CustomStreamWrapper] = litellm_completion(
                        model,
                        messages,
                        stream=stream,
                        custom_llm_provider=self._config.custom_llm_provider,
                        input_cost_per_token=0,
                        output_cost_per_token=0,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        base_url=self._config.base_url,
                        provider=provider,
                        api_key=private_auth,
                        **kwargs,
                    )
                    break
                except Exception as e:
                    if i == self._config.num_inference_retries - 1:
                        raise ValueError(f"Bad request: {e}") from None

            return result

        self.completions = completions

        def query_vector_store(
            vector_store_id: str, query: str, full_files: bool = False
        ) -> Union[List[SimilaritySearch], List[SimilaritySearchFile]]:
            """Query a vector store."""
            if self._config is None:
                raise ValueError("Missing NearAI Hub config")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {private_auth}",
            }

            data = {"query": query, "full_files": full_files}

            endpoint = f"{self._config.base_url}/vector_stores/{vector_store_id}/search"

            try:
                response = requests.post(endpoint, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                raise ValueError(f"Error querying vector store: {e}") from None

        self.query_vector_store = query_vector_store

        def upload_file(
            file_content: str,
            purpose: Literal["assistants", "batch", "fine-tune", "vision"],
            encoding: str = "utf-8",
            file_name="file.txt",
            file_type="text/plain",
        ) -> FileObject:
            """Uploads a file."""
            client = openai.OpenAI(base_url=self._config.base_url, api_key=private_auth)
            file_data = io.BytesIO(file_content.encode(encoding))
            return client.files.create(file=(file_name, file_data, file_type), purpose=purpose)

        self.upload_file = upload_file

        def add_file_to_vector_store(vector_store_id: str, file_id: str) -> VectorStoreFile:
            """Adds a file to vector store."""
            client = openai.OpenAI(base_url=self._config.base_url, api_key=private_auth)
            return client.beta.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_id)

        self.add_file_to_vector_store = add_file_to_vector_store

        def create_vector_store_from_source(
            name: str,
            source: Union[GitHubSource, GitLabSource],
            source_auth: Optional[str] = None,
            chunking_strategy: Optional[ChunkingStrategy] = None,
            expires_after: Optional[ExpiresAfter] = None,
            metadata: Optional[Dict[str, str]] = None,
        ) -> VectorStore:
            """Creates a vector store from the given source.

            Args:
            ----
                name (str): The name of the vector store.
                source (Union[GitHubSource, GitLabSource]): The source from which to create the vector store.
                source_auth (Optional[str]): The source authentication token.
                chunking_strategy (Optional[ChunkingStrategy]): The chunking strategy to use.
                expires_after (Optional[ExpiresAfter]): The expiration policy.
                metadata (Optional[Dict[str, str]]): Additional metadata.

            Returns:
            -------
                VectorStore: The created vector store.

            """
            print(f"Creating vector store from source: {source}")
            headers = {
                "Authorization": f"Bearer {private_auth}",
                "Content-Type": "application/json",
            }
            data = {
                "name": name,
                "source": source,
                "source_auth": source_auth,
                "chunking_strategy": chunking_strategy,
                "expires_after": expires_after,
                "metadata": metadata,
            }
            endpoint = f"{self._config.base_url}/vector_stores/from_source"

            try:
                response = requests.post(endpoint, headers=headers, json=data)
                print(response.json())
                response.raise_for_status()
                return VectorStore(**response.json())
            except requests.RequestException as e:
                raise ValueError(f"Failed to create vector store: {e}") from None

        self.create_vector_store_from_source = create_vector_store_from_source

        def create_vector_store(
            name: str,
            file_ids: List[str],
            expires_after: Union[ExpiresAfter, NotGiven] = NOT_GIVEN,
            chunking_strategy: Union[
                AutoFileChunkingStrategyParam, StaticFileChunkingStrategyParam, NotGiven
            ] = NOT_GIVEN,
            metadata: Optional[Dict[str, str]] = None,
        ) -> VectorStore:
            """Creates Vector Store.

            :param name: Vector store name.
            :param file_ids: Files to be added to the vector store.
            :param expires_after: Expiration policy.
            :param chunking_strategy: Chunking strategy.
            :param metadata: Additional metadata.
            :return: Returns the created vector store or error.
            """
            client = openai.OpenAI(base_url=self._config.base_url, api_key=private_auth)
            return client.beta.vector_stores.create(
                file_ids=file_ids,
                name=name,
                expires_after=expires_after,
                chunking_strategy=chunking_strategy,
                metadata=metadata,
            )

        self.create_vector_store = create_vector_store

        def create_thread(messages):
            """Create a thread."""
            return private_client.beta.threads.create(messages=messages)

        self.create_thread = create_thread

        def threads_messages_create(thread_id: str, content: str, role: Literal["user", "assistant"]):
            """Create a message in a thread."""
            return private_client.beta.threads.messages.create(thread_id=thread_id, content=content, role=role)

        self.threads_messages_create = threads_messages_create

        def threads_create_and_run_poll(assistant_id: str, model: str, messages: List[ChatCompletionMessageParam]):
            """Create a thread and run the assistant."""
            thread = self.create_thread(messages)
            return private_client.beta.threads.create_and_run_poll(
                thread=thread, assistant_id=assistant_id, model=model
            )

        self.threads_create_and_run_poll = threads_create_and_run_poll

        def threads_list_messages(thread_id: str, order: Literal["asc", "desc"] = "asc"):
            """List messages in a thread."""
            return private_client.beta.threads.messages.list(thread_id=thread_id, order=order)

        self.threads_list_messages = threads_list_messages

        def threads_fork(thread_id: str):
            """Fork a thread."""
            forked_thread = private_client.post(
                path=f"{self._config.base_url}/threads/{thread_id}/fork", cast_to=Thread
            )
            return forked_thread

        self.threads_fork = threads_fork

        def threads_runs_create(thread_id: str, assistant_id: str, model: str):
            """Create a run in a thread."""
            return private_client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id, model=model)

        self.threads_runs_create = threads_runs_create

        def run_agent(current_run_id: str, child_thread_id: str, assistant_id: str):
            """Starts a child agent run from a parent agent run."""
            return private_client.beta.threads.runs.create(
                thread_id=child_thread_id,
                assistant_id=assistant_id,
                extra_body={"parent_run_id": current_run_id},
            )

        self.run_agent = run_agent

        def query_user_memory(query: str):
            """Query the user memory."""
            return private_client.post(
                path=f"{self._config.base_url}/vector_stores/memory/query",
                body={"query": query},
                cast_to=str,
            )

        self.query_user_memory = query_user_memory

        def add_user_memory(memory: str):
            """Add user memory."""
            return private_client.post(
                path=f"{self._config.base_url}/vector_stores/memory",
                body={"memory": memory},
                cast_to=str,
            )

        self.add_user_memory = add_user_memory

        def generate_image(prompt: str):
            """Generate an image."""
            return private_client.images.generate(prompt=prompt)

        self.generate_image = generate_image

    # This makes sense in the CLI where we don't mind doing this request and caching it.
    # In the aws_runner this is an extra request every time we run.
    # TODO(#233): add a choice of a provider model in aws_runner, and then this step can be skipped.
    @property
    def provider_models(self) -> ProviderModels:  # noqa: D102
        return ProviderModels(self._config)

    def get_vector_store(self, vector_store_id: str) -> VectorStore:
        """Gets a vector store by id."""
        endpoint = f"{self._config.base_url}/vector_stores/{vector_store_id}"
        response = requests.get(endpoint)
        response.raise_for_status()
        return VectorStore(**response.json())
