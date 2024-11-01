from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import List, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from lean_dojo import Dojo, LeanGitRepo, ProofFinished, TacticState, Theorem
from pydantic import BaseModel
from shared.client_config import ClientConfig
from shared.inference_client import InferenceClient

from nearai.agents.agent import Agent
from nearai.agents.environment import Environment
from nearai.config import CONFIG, get_hub_client
from nearai.dataset import get_dataset
from nearai.solvers import SolverStrategy


class LeanDatum(BaseModel):
    url: str
    commit: str
    filename: str
    theorem: str


@dataclass
class LeanTaskInfo:
    url: str
    commit: str
    filename: str
    theorem: str
    theorem_raw: str


def load_repository(url: str) -> str:
    if url == "https://github.com/yangky11/miniF2F-lean4":
        return str(get_dataset("au.near/github_com_yangky11_miniF2F-lean4/0.0.1", verbose=False))

    print(
        "Repository not found on the registry. You need to setup Github credentials to download repository. See https://leandojo.readthedocs.io/en/latest/getting-started.html#"
    )
    return url


def load_theorem(task: LeanDatum) -> str:
    """Use local copy of the repository."""
    repo = LeanGitRepo(task.url, task.commit)
    theorem = Theorem(repo, task.filename, task.theorem)
    with Dojo(theorem) as (_, state):
        return state.pp


def check_solution(task: LeanDatum, solution: List[str]) -> bool:
    repo = LeanGitRepo(task.url, task.commit)
    theorem = Theorem(repo, task.filename, task.theorem)

    with Dojo(theorem) as (dojo, state):
        for tactic in solution:
            result = dojo.run_tac(state, tactic)

            if isinstance(result, TacticState):
                state = result

            elif isinstance(result, ProofFinished):
                # TODO: Check if the proof uses sorry (or is there any other hack)
                return True

            else:
                return False

    return False


class LeanEnvironment(Environment):
    def __init__(self, agent: Agent, lean_datum: LeanDatum):
        """Initialize the Lean environment."""
        self.tdir = TemporaryDirectory()
        self.lean_info = LeanTaskInfo(
            lean_datum.url,
            lean_datum.commit,
            lean_datum.filename,
            lean_datum.theorem,
            load_theorem(lean_datum),
        )

        client_config = ClientConfig(
            base_url=CONFIG.nearai_hub.base_url,
            auth=CONFIG.auth,
        )
        client = InferenceClient(client_config)
        hub_client = get_hub_client()
        thread = hub_client.beta.threads.create()

        self.tactics = []

        super().__init__(
            self.tdir.name,
            [agent],
            client,
            hub_client,
            thread.id,
            "run_id",
            "",
            approvals={"confirm_execution": lambda _: False},
        )


class LeanSolverStrategy(SolverStrategy):
    """Solver strategy for the MBPP dataset."""

    def __init__(  # noqa: D107
        self,
        dataset_ref: Union[Dataset, DatasetDict],
        model: str = "",
        agent: str = "",
    ) -> None:
        super().__init__(model, agent)

    def evaluation_name(self) -> str:  # noqa: D102
        return "lean"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["lean"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        lean_datum = LeanDatum.model_validate(datum)
        lean_datum.url = load_repository(lean_datum.url)

        # TODO: Remove print statements

        assert self.agent_obj is not None
        env = LeanEnvironment(self.agent_obj, lean_datum)
        print("Running Lean solver...")
        env.run(new_message=None, max_iterations=16)
        print("Finish running...")
        print("Is done:", env.is_done())
        print("Solution:", env.tactics)

        if not env.is_done() or not env.tactics:
            return False

        print("Check solution...")
        result = check_solution(lean_datum, env.tactics)
        print("Result:", result)
        exit(0)
        return result
