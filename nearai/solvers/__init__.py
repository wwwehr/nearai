from abc import ABC, ABCMeta, abstractmethod
from typing import Any, Dict, List, Tuple, Union


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
        """Returns the name of the solver strategy."""
        return type(self).__name__

    @abstractmethod
    def compatible_datasets(self) -> List[str]:
        """Returns the list of datasets that the solver strategy is compatible with."""
        ...

    @abstractmethod
    def solve(self, datum: dict) -> Union[bool, Tuple[bool, Any]]:
        """Solves the task for the given datum."""
        ...


SolverStrategyRegistry: Dict[str, SolverStrategy] = {}

from nearai.solvers.ddot_v0_solver import DDOTSV0Solver  # noqa: E402
from nearai.solvers.hellaswag_solver import HellaswagSolverStrategy  # noqa: E402
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
]
