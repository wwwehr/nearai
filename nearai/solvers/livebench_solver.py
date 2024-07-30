import ast
import re
from itertools import islice

from jinja2 import Template
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from typing import List, Tuple, Union
from datasets import Dataset, DatasetDict

from nearai.solvers import SolverScoringMethod, SolverStrategy, classproperty
from nearai.config import CONFIG, PROMPTS_FOLDER
from nearai.completion import InferenceRouter


class LiveBenchSolverStrategy(SolverStrategy):
    """
    Solver strategy for the live bench dataset
    """

    def __init__(self, dataset_ref: str, model):
        super().__init__()
        self.dataset_ref = dataset_ref
        self.completion_fn = InferenceRouter(CONFIG.llm_config).completions
        self.model = model

    def compatible_datasets(self) -> List[str]:
        return ["live_bench"]
    
    def get_custom_tasks(self) -> List[dict]:
        return [{'summary': 'all'}]
    
    @classproperty
    def scoring_method(cls) -> SolverScoringMethod:
        return SolverScoringMethod.Custom

    def solve(self, _datum: dict) -> Tuple[bool, str]:
        return True, "Called solve()"
