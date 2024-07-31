from abc import ABC, ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Tuple, Union


class SolverScoringMethod(Enum):
    # Scores each question with 'True' or 'False'.
    TrueOrFalseList = "TrueOrFalseList"
    # Custom dataset with custom answers.
    Custom = "Custom"


class SolverStrategyClassProperty:
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, _owner_self, owner_cls):
        return self.fget(owner_cls)


class SolverStrategyMeta(ABCMeta):
    """Metaclass that automatically registers subclasses in the SolverStrategyRegistry."""

    def __new__(cls, name: str, bases: tuple, namespace: dict) -> Any:
        new_class = super().__new__(cls, name, bases, namespace)
        if bases != (ABC,):  # Avoid registering the abstract base class itself
            SolverStrategyRegistry[new_class.__name__] = new_class  # type: ignore
        return new_class


class SolverStrategy(ABC, metaclass=SolverStrategyMeta):
    """Abstract class for solver strategies."""

    def __init__(self) -> None:
        pass

    @property
    def name(self) -> str:
        return type(self).__name__

    @SolverStrategyClassProperty
    def scoring_method(self) -> SolverScoringMethod:
        return SolverScoringMethod.TrueOrFalseList

    @abstractmethod
    def compatible_datasets(self) -> List[str]: ...

    @abstractmethod
    def solve(self, datum: dict) -> Union[bool, Tuple[bool, Any]]: ...

    def get_custom_tasks(self) -> List[dict]:
        if self.scoring_method == SolverScoringMethod.Custom:
            raise NotImplementedError("get_custom_tasks must be implemented for Custom scoring method")
        else:
            raise AttributeError("get_custom_tasks is only applicable for Custom scoring method")


SolverStrategyRegistry: Dict[str, SolverStrategy] = {}

from nearai.solvers.ddot_v0_solver import DDOTSV0Solver  # noqa: E402
from nearai.solvers.hellaswag_solver import HellaswagSolverStrategy  # noqa: E402
from nearai.solvers.livebench_solver import LiveBenchSolverStrategy  # noqa: E402
from nearai.solvers.mbpp_agent_solver import MBPPSolverAgent  # noqa: E402
from nearai.solvers.mbpp_solver import MBPPSolverStrategy  # noqa: E402
from nearai.solvers.mmlu_solver import MMLUSolverStrategy  # noqa: E402

__all__ = [
    "SolverStrategyRegistry",
    "DDOTSV0Solver",
    "MBPPSolverStrategy",
    "MBPPSolverAgent",
    "MMLUSolverStrategy",
    "HellaswagSolverStrategy",
    "LiveBenchSolverStrategy",
]
