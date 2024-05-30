import concurrent.futures
from itertools import islice
from typing import Tuple

from datasets import Dataset
from tqdm import tqdm

from .solvers import SolverStrategy


class BenchmarkExecutor:
    def __init__(self, dataset_info: Tuple[str, str, Dataset], solver_strategy: SolverStrategy):
        self.dataset_info = dataset_info
        self.solver_strategy = solver_strategy

    def run(self, progress: bool = True, max_concurrent: int = 32) -> None:

        _, subset, dataset = self.dataset_info
        if subset is not None:
            dataset = dataset[subset]
        assert isinstance(dataset, Dataset), f"Expected a Dataset, got {type(dataset)}"

        correct = 0
        remaining = len(dataset)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            tasks = iter(
                executor.submit(self.solver_strategy.solve, datum=datum) for datum in dataset
            )
            total = len(dataset)
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
                    if result:
                        correct += 1
                    bar.set_description(f"Correct/Seen - {correct}/{total - remaining} - {correct/(total - remaining):.2%}")

                    try:
                        next_task = next(tasks)
                        futures.append(next_task)
                    except StopIteration:
                        continue

        print(f"Final score: {correct}/{total} - {correct/total:.2%}")
