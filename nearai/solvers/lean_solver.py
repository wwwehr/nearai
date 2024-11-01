import json
from typing import List, Optional, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from jinja2 import Template
from lean_dojo import Dojo, LeanGitRepo, ProofFinished, TacticState, Theorem
from pydantic import BaseModel

from nearai.config import PROMPTS_FOLDER
from nearai.solvers import SolverStrategy


class LeanDatum(BaseModel):
    task_id: int
    url: str
    commit: str
    filepath: str
    theorem_name: str


BEGIN_MARKER = "!JSON_BEGIN"
END_MARKER = "!JSON_END"


def load_theorem(lean_datum: LeanDatum) -> str:
    repo = LeanGitRepo(lean_datum.url, lean_datum.commit)
    theorem = Theorem(repo, lean_datum.filepath, lean_datum.theorem_name)
    with Dojo(theorem) as (_, state):
        return state.pp


def prepare_prompt(lean_datum: LeanDatum) -> str:
    theorem = load_theorem(lean_datum)
    return Template(open(PROMPTS_FOLDER / "lean_verbose_answer.js").read(), trim_blocks=True).render(
        **lean_datum.model_dump(),
        theorem=theorem,
        theorem_raw=repr(theorem),
        begin_marker=BEGIN_MARKER,
        end_marker=END_MARKER,
    )


def extract_answer(response: str) -> Optional[List[str]]:
    begin = response.find(BEGIN_MARKER)
    if begin == -1:
        return None

    end = response.find(END_MARKER, begin)
    if end == -1:
        return None

    content = response[begin + len(BEGIN_MARKER) : end]
    content.strip(" \n")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def check_solution(task: LeanDatum, solution: List[str]) -> bool:
    repo = LeanGitRepo(task.url, task.commit)
    theorem = Theorem(repo, task.filepath, task.theorem_name)

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


class LeanSolverStrategy(SolverStrategy):
    """Solver strategy for the MBPP dataset."""

    def __init__(  # noqa: D107
        self,
        dataset_ref: Union[Dataset, DatasetDict],
        model: str = "",
        agent: str = "",
        shots: int = 3,
    ) -> None:
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref
        self.shots = shots

    def evaluation_name(self) -> str:  # noqa: D102
        return f"mbpp_{self.shots}shots"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["lean"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        lean_datum = LeanDatum.model_validate(datum)
        prompt = prepare_prompt(lean_datum)
        response = self.start_inference_session(lean_datum.task_id).run_task(prompt)
        tactics = extract_answer(response)
        return tactics is not None and check_solution(lean_datum, tactics)
