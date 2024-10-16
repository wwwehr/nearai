import logging

from aws_runner.service import run_with_environment

DEFAULT_OUTPUT_PATH = "/tmp/nearai/conversations/"

logger = logging.getLogger(__name__)


class LocalRunner:
    def __init__(  # noqa: D107
        self,
        path,
        agents,
        thread_id,
        run_id,
        auth,
        params,
    ) -> None:
        print(
            f"Initializing LocalRunner with path: {path}, agents: {agents}, thread_id: {thread_id},"
            f"run_id: {run_id}, auth: {auth}, params: {params}"
        )

        self._agents = agents
        self._confirm_commands = True
        run_with_environment(agents, auth, thread_id, run_id, params=params)
