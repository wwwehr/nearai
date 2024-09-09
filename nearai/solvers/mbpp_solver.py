import ast
import os
import random
import re
from itertools import islice
import time
from typing import Any, Dict, List, Optional, Union, cast

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from jinja2 import Template
from litellm import Choices, ModelResponse
from pydantic import BaseModel

from hub.api.near.primitives import get_provider_model
from nearai.agent import load_agent
from nearai.completion import InferenceRouter
from nearai.config import CONFIG, DEFAULT_PROVIDER, PROMPTS_FOLDER
from nearai.environment import Environment
from nearai.solvers import SolverStrategy


def get_function_name(code_str: str) -> str:
    parsed = ast.parse(code_str)
    function_name = None
    for node in ast.walk(parsed):
        if isinstance(node, ast.FunctionDef):
            function_name = node.name
            break
    assert function_name is not None, "No function definition found in code string."
    return function_name


def parse_python_code_block(answer_text: str) -> List[str]:
    pattern = r"```python\n(.*?)\n```"
    code_blocks = re.findall(pattern, answer_text, re.DOTALL)
    return code_blocks


def parse_code_block(answer_text: str) -> List[str]:
    pattern = r"```\n(.*?)\n```"
    code_blocks = re.findall(pattern, answer_text, re.DOTALL)
    return code_blocks


class MBPPDatum(BaseModel):
    task_id: int
    text: str
    code: str
    test_list: List[str]
    challenge_test_list: List[str]


class MBPPSolverStrategy(SolverStrategy):
    """Solver strategy for the MBPP dataset."""

    SHOTS = 3

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], agent: str) -> None:  # noqa: D107
        super().__init__()
        self.dataset_ref = dataset_ref
        self.agent = load_agent(agent)

    def evaluation_name(self) -> str:  # noqa: D102
        return "mbpp"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["mbpp"]

    def model_metadata(self) -> Optional[Dict[str, Any]]:  # noqa: D102
        return {"name": "llama-v3p1-405b-instruct"}

    def agent_metadata(self) -> Optional[Dict[str, Any]]:  # noqa: D102
        return self.agent.metadata

    def evaluated_entry_namespace(self) -> str:  # noqa: D102
        # Only provider models are supported.
        return self.agent.namespace

    def model_provider(self) -> str:  # noqa: D102
        return DEFAULT_PROVIDER

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = MBPPDatum(**datum).model_dump()

        ## Allow LLM to think "out loud" for it's answer
        function_name = get_function_name(datum["code"])
        example_problems = list(islice(self.dataset_ref["prompt"], self.SHOTS))
        base_prompt = Template(open(PROMPTS_FOLDER / "mbpp_verbose_answer.j2").read(), trim_blocks=True).render(
            function_name=function_name,
            example_problems=example_problems,
            challenge_problem=datum,
        )

        path = os.path.join(
            "/tmp",
            "mbpp",
            str(datum["task_id"]),
            str(int(time.time() * 1000)),
            str(random.randint(0, 1000)),
        )
        CONFIG.confirm_commands = False
        env = Environment(path, [self.agent], CONFIG)
        task = base_prompt

        env.run_task(task, max_iterations=1)
        output = ""
        messages = env.list_messages()
        i = len(messages)
        while output == "":
            i = i - 1
            if i < 0 or messages[i]["role"] == "user":
                break
            if messages[i]["role"] == "assistant":
                output = messages[i]["content"]
        response = output

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "mbpp_extract_answer.j2").read(), trim_blocks=True
        ).render(
            function_name=function_name,
            answer_text=response,
        )
        task = extract_answer_prompt

        env = Environment(path, [self.agent], CONFIG)
        env.run_task(task, max_iterations=1)
        output = ""
        messages = env.list_messages()
        i = len(messages)
        while output == "":
            i = i - 1
            if i < 0 or messages[i]["role"] == "user":
                break
            if messages[i]["role"] == "assistant":
                output = messages[i]["content"]
        response = output

        ## Parse the python code
        python_code_blocks = parse_python_code_block(response) + parse_code_block(response)
        code = ""
        if len(python_code_blocks) == 0:
            code = response
        else:
            code = python_code_blocks[0]

        ## Evaluate the code
        try:
            for test in datum["test_list"] + datum["challenge_test_list"]:
                test_code = code + "\n" + test
                exec(test_code)
            return True
        except Exception:
            return False
