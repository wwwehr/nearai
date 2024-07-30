import concurrent.futures
import json
from dataclasses import dataclass
from functools import partial
from itertools import islice
from typing import Any, Callable, Dict, Optional, Tuple, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from tqdm import tqdm

from nearai.db import db
from nearai.solvers import SolverScoringMethod, SolverStrategy


@dataclass
class DatasetInfo:
    name: str
    subset: Optional[str]
    dataset: Union[Dataset, DatasetDict]

    def get_dataset(self) -> Dataset:  # noqa: D102
        if isinstance(self.dataset, DatasetDict):
            assert (
                self.subset is not None
            ), f"Subset must be: {', '.join(self.dataset.keys())}"
            return self.dataset[self.subset]
        elif isinstance(self.dataset, Dataset):
            return self.dataset
        else:
            raise ValueError(
                f"Expected a Dataset or DatasetDict, got {type(self.dataset)}"
            )


class BenchmarkExecutor:
    def __init__(  # noqa: D107
        self,
        dataset_info: DatasetInfo,
        solver_strategy: SolverStrategy,
        benchmark_id: int,
    ):
        self.dataset_info = dataset_info
        self.solver_strategy = solver_strategy
        self.benchmark_id = benchmark_id

    def run(self, progress: bool = True, max_concurrent: int = 1) -> None:  # noqa: D102
        data_tasks = (
            self.dataset_info.get_dataset()
            if self.solver_strategy.scoring_method != SolverScoringMethod.Custom
            else self.solver_strategy.get_custom_tasks()
        )

        cache_map: Dict[SolverScoringMethod, Callable[[], Any]] = {
            SolverScoringMethod.TrueOrFalseList: lambda: db.get_benchmark_status(
                self.benchmark_id
            ),
            SolverScoringMethod.Custom: lambda: db.get_benchmark_results(
                self.benchmark_id
            ),
        }

        cache = cache_map[self.solver_strategy.scoring_method]()

        n_true_results = 0
        remaining = len(data_tasks)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            task_ctor = partial(
                solve_task,
                benchmark_id=self.benchmark_id,
                cache=cache,
                solve_fn=self.solver_strategy.solve,
            )
            tasks = iter(
                executor.submit(task_ctor, index=index, datum=datum)
                for index, datum in enumerate(data_tasks)
            )

            total = len(data_tasks)
            bar = tqdm(total=total, disable=not progress)
            futures = list(islice(tasks, max_concurrent))
            while futures:
                completed, ongoing_futures = concurrent.futures.wait(
                    futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                futures = list(ongoing_futures)
                for completed_future in completed:
                    bar.update(1)
                    remaining -= 1

                    result = completed_future.result()
                    status = result
                    info = ""
                    if isinstance(result, tuple):
                        status, info = result
                    if status:
                        n_true_results += 1
                    if (
                        self.solver_strategy.scoring_method
                        == SolverScoringMethod.TrueOrFalseList
                    ):
                        bar.set_description(
                            f"Correct/Seen - {n_true_results}/{total - remaining} - {n_true_results/(total - remaining):.2%}"  # noqa: E501
                        )
                    elif info != "":
                        print(info)

                    try:
                        next_task = next(tasks)
                        futures.append(next_task)
                    except StopIteration:
                        continue

        if self.solver_strategy.scoring_method == SolverScoringMethod.TrueOrFalseList:
            print(f"Final score: {n_true_results}/{total} - {n_true_results/total:.2%}")


def solve_task(
    benchmark_id: int,
    cache: Union[Dict[int, bool], Dict[int, Tuple[bool, str]]],
    solve_fn: Callable[[Any], Union[bool, Tuple[bool, Any]]],
    index: int,
    datum: Any,
) -> Union[bool, Tuple[bool, Any]]:
    if index in cache:
        return cache[index]

    result = solve_fn(datum)
    status = result
    info = ""

    if isinstance(result, tuple):
        status, info = result

    db.update_benchmark_result(benchmark_id, index, status, json.dumps(info))

    return result
