import os
from datetime import date, datetime
from typing import List, Union

import pytz
from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from pydantic import BaseModel

from nearai.solvers import SolverStrategy


class ShellTaskDatum(BaseModel):
    input: str
    input_file: str
    input_file_content: str
    response: str
    output_file: str
    output_file_content: str
    steps: str


class ShellBenchmarkSolverStrategy(SolverStrategy):
    """Solver strategy for the nearai shell dataset."""

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = "") -> None:  # noqa: D107
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref

    def evaluation_name(self) -> str:  # noqa: D102
        return "shell_benchmark"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["shell_benchmark"]

    def _is_good_response(self, response: str, correct_answer: str) -> bool:
        response = response.strip()
        correct_answer = correct_answer.strip()

        if correct_answer == "<date>":
            current_date = date.today()
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are '{response}' and '{current_date}' represent the same date? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        if correct_answer == "<day_of_week>":
            current_date = date.today()
            day_of_week = current_date.strftime("%A")
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are '{response}' and '{day_of_week}' represent the same day of week? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        if correct_answer == "<utc_time>":
            utc_time = datetime.now(pytz.UTC).strftime("%H:%M")
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are times '{response}' and '{utc_time}' within few minutes? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        if correct_answer == "<local_time>":
            local_time = datetime.now().strftime("%H:%M")
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are times '{response}' and '{local_time}' within few minutes? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        return response == correct_answer

    def solve(self, datum: dict) -> bool:  # noqa: D102
        task = ShellTaskDatum(**datum)
        print("-----------------------------------------------------------------------------------------------------")
        print(f"[input] {task.input}")

        session = self.start_inference_session("")
        print(f"[path] {session.path}")
        if task.steps:
            session.steps_per_task = int(task.steps)
        if task.input_file:
            file_path = os.path.join(session.path, task.input_file)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(os.path.join(session.path, task.input_file), "w") as f:
                f.write(task.input_file_content)

        response = session.run_task(task.input)

        if task.response:
            if not self._is_good_response(response, task.response):
                return False

        if task.output_file:
            if not os.path.exists(os.path.join(session.path, task.output_file)):
                return False
            if task.output_file_content:
                with open(os.path.join(session.path, task.output_file), "r") as f:
                    if f.read().strip() != task.output_file_content:
                        return False

        print("Correct")
        print("-----------------------------------------------------------------------------------------------------")
        return True
