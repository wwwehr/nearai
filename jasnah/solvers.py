import ast
import re
from abc import ABC, ABCMeta, abstractmethod
from itertools import islice
from textwrap import dedent
from typing import Any, Callable, Dict, List

from datasets import Dataset  # type: ignore
from jinja2 import Template
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from .config import PROMPTS_FOLDER


class SolverStrategyMeta(ABCMeta):
    """
    Metaclass that automatically registers subclasses in the SolverStrategyRegistry.
    """

    def __new__(cls, name: str, bases: tuple, namespace: dict) -> Any:
        new_class = super().__new__(cls, name, bases, namespace)
        if bases != (ABC,):  # Avoid registering the abstract base class itself
            SolverStrategyRegistry[new_class.__name__] = new_class  # type: ignore
        return new_class


class SolverStrategy(ABC, metaclass=SolverStrategyMeta):
    """
    Abstract class for solver strategies.
    """

    def __init__(self, completion_fn: Callable[[Any], ChatCompletion]):
        self.completion_fn = completion_fn

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    def compadible_datasets(self) -> List[str]:
        ...

    @abstractmethod
    def solve(self, datum: dict) -> bool:
        ...


SolverStrategyRegistry: Dict[str, SolverStrategy] = {}


class MBPPSolverStrategy(SolverStrategy):
    """
    Solver strategy for the MBPP dataset
    """

    SHOTS = 3

    def __init__(self, completion_fn: Callable[[Any], ChatCompletion], dataset_ref: Dataset):
        super().__init__(completion_fn)
        self.dataset_ref = dataset_ref
        self.completion_fn = completion_fn

    def compadible_datasets(self) -> List[str]:
        return ["mbpp"]

    def solve(self, datum: dict) -> bool:
        def get_function_name(code_str: str) -> str:
            parsed = ast.parse(code_str)
            function_name = None
            for node in ast.walk(parsed):
                if isinstance(node, ast.FunctionDef):
                    function_name = node.name
                    break
            assert function_name is not None, "No function definition found in code string."
            return function_name

        def parse_python_code_block(answer_text: str) -> list[str]:
            pattern = r"```python\n(.*?)\n```"
            code_blocks = re.findall(pattern, answer_text, re.DOTALL)
            return code_blocks

        def parse_code_block(answer_text: str) -> list[str]:
            pattern = r"```\n(.*?)\n```"
            code_blocks = re.findall(pattern, answer_text, re.DOTALL)
            return code_blocks

        class MBPPDatum(BaseModel):
            task_id: int
            text: str
            code: str
            test_list: List[str]

        datum = MBPPDatum(**datum).model_dump()

        ## Allow LLM to think "out loud" for it's answer
        function_name = get_function_name(datum["code"])
        example_problems = list(islice(self.dataset_ref["prompt"], self.SHOTS))
        base_prompt = Template(
            open(PROMPTS_FOLDER / "mbpp_verbose_answer.j2").read(), trim_blocks=True
        ).render(
            function_name=function_name,
            example_problems=example_problems,
            challenge_problem=datum,
        )
        completion_response: ChatCompletion = self.completion_fn(  # type: ignore
            messages=[
                {"role": "system", "content": base_prompt},
            ],
            temperature=0.0,
        )
        response = str(completion_response.choices[0].message.content)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "mbpp_extract_answer.j2").read(), trim_blocks=True
        ).render(
            function_name=function_name,
            answer_text=response,
        )
        completion_response = self.completion_fn(  # type: ignore
            messages=[
                {"role": "system", "content": extract_answer_prompt},
            ],
            temperature=0.0,
        )
        response = str(completion_response.choices[0].message.content)

        ## Parse the python code
        python_code_blocks = parse_python_code_block(response) + parse_code_block(response)
        code = ""
        if len(python_code_blocks) == 0:
            code = response
        else:
            code = python_code_blocks[0]

        ## Evaluate the code
        try:
            for test in datum["test_list"]:
                test_code = code + "\n" + test
                exec(test_code)
            return True
        except:
            return False


class MMLUSolverStrategy(SolverStrategy):
    """
    Solver strategy for the MMLU dataset
    """

    SHOTS = 8

    def __init__(self, completion_fn: Callable[[Any], ChatCompletion], dataset_ref: Dataset):
        super().__init__(completion_fn)
        self.dataset_ref = dataset_ref
        self.completion_fn = completion_fn

    def compadible_datasets(self) -> List[str]:
        return ["mmlu"]

    def solve(self, datum: dict) -> bool:
        class MMLUDatum(BaseModel):
            question: str
            subject: str
            choices: list[str]
            answer: int

        datum = MMLUDatum(**datum).model_dump()

        choices = ["A", "B", "C", "D"]
        example_problems_indices = list(range(0, 5 * self.SHOTS, 5))
        example_problems = list(
            map(
                lambda d: MMLUDatum(**d).model_dump(),
                [self.dataset_ref["dev"][i] for i in example_problems_indices],
            )
        )
        base_prompt = Template(
            open(PROMPTS_FOLDER / "mmlu_verbose_answer.j2").read(), trim_blocks=True
        ).render(
            example_problems=example_problems,
            challenge_problem=datum,
            choices=choices,
        )
        completion_response: ChatCompletion = self.completion_fn(  # type: ignore
            messages=[
                {"role": "system", "content": base_prompt},
            ],
            temperature=0.2,
        )
        response = str(completion_response.choices[0].message.content)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "mmlu_extract_answer.j2").read(), trim_blocks=True
        ).render(
            challenge_problem=datum,
            answer_text=response,
            choices=choices,
        )
        completion_response = self.completion_fn(  # type: ignore
            messages=[
                {"role": "system", "content": extract_answer_prompt},
            ],
            temperature=0.0,
        )
        response = str(completion_response.choices[0].message.content)

        try:
            answer = choices.index(response)
            return bool(answer == datum["answer"])
        except:
            print("Failed to parse answer")
            return False


class HellswagSolverStrategy(SolverStrategy):
    """
    Solver strategy for the MMLU dataset
    """

    SHOTS = 8

    def __init__(self, completion_fn: Callable[[Any], ChatCompletion], dataset_ref: Dataset):
        super().__init__(completion_fn)
        self.dataset_ref = dataset_ref
        self.completion_fn = completion_fn

    def compadible_datasets(self) -> List[str]:
        return ["hellaswag"]

    def solve(self, datum: dict) -> bool:
        class HellaswagDatum(BaseModel):
            activity_label: str
            ctx: str
            ctx_a: str
            ctx_b: str
            endings: list[str]
            ind: int
            label: str
            source_id: str
            split: str
            split_type: str

        datum = HellaswagDatum(**datum).model_dump()

        choices = ["A", "B", "C", "D"]
        example_problems_indices = list(range(0, 5 * self.SHOTS, 5))
        example_problems = list(
            map(
                lambda d: HellaswagDatum(**d).model_dump(),
                [self.dataset_ref["validation"][i] for i in example_problems_indices],
            )
        )
        base_prompt = Template(
            open(PROMPTS_FOLDER / "hellaswag_verbose_answer.j2").read(), trim_blocks=True
        ).render(
            example_problems=example_problems,
            challenge_problem=datum,
            choices=choices,
        )
        completion_response: ChatCompletion = self.completion_fn(  # type: ignore
            messages=[
                {"role": "system", "content": base_prompt},
            ],
            temperature=0.2,
        )
        response = str(completion_response.choices[0].message.content)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "hellaswag_extract_answer.j2").read(), trim_blocks=True
        ).render(
            challenge_problem=datum,
            answer_text=response,
            choices=choices,
        )
        completion_response = self.completion_fn(  # type: ignore
            messages=[
                {"role": "system", "content": extract_answer_prompt},
            ],
            temperature=0.0,
        )
        response = str(completion_response.choices[0].message.content)

        try:
            answer = choices.index(response)
            return bool(answer == datum["label"])
        except:
            print("Failed to parse answer")
            return False
