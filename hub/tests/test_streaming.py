from unittest import TestCase

import json
import openai
import pytest
from fastapi.testclient import TestClient
from nearai.config import load_config_file

from openapi_client import Message
from shared.models import Delta
from openai.types.beta.threads import TextContentBlock
from openai.types.beta.threads import Text

from sqlmodel import Session, SQLModel, create_engine
from hub.app import app
from hub.api.v1.models import get_session
from sqlmodel.pool import StaticPool

class Test(TestCase):
    @pytest.fixture(name="session", autouse=True)
    def session_fixture(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    @pytest.fixture(name="client", autouse=True)
    def client_fixture(self, autouse=True):
        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override

        self.client = TestClient(app)
        yield self.client
        app.dependency_overrides.clear()

    def setUp(self):
        auth = load_config_file()["auth"]
        self.signature = json.dumps(auth)

    def create_openai_client(self):
        url = str(self.client.base_url) + "/v1"
        return openai.OpenAI(api_key=self.signature, base_url=url, http_client=self.client)

    def test_create_delta(self):
        compatibility_client = self.create_openai_client()

        thread = compatibility_client.beta.threads.create()
        messages = compatibility_client.beta.threads.messages.list(thread_id=thread.id).data
        assert len(messages) == 0

        message =  compatibility_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="test",# {"type": "text", "text": ""},# [MessageContent(TextContentBlock(text=Text(value="", annotations=[]), type="text")], # [TextContentBlock(type="text", text={"value": "hello", "annotations": []})],
            extra_body={
                "assistant_id": "unittest",
            },
        )

        delta = Delta(content={
            "index": 0,
            "type": "text",
            "text": { "value": "the answer is 42", "annotations": [] }
        })
        headers = {"Authorization": f"Bearer {self.signature}"}
        response = self.client.post(f"/v1/threads/{thread.id}/messages/{message.id}/deltas", json=delta.model_dump(), headers=headers)

        assert response.status_code == 200

        messages = compatibility_client.beta.threads.messages.list(thread_id=thread.id).data
        assert len(messages) == 1