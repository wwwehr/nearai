# Building and running a benchmark

In the context of software engineering, the purpose of a benchmark is to associate some performance metric (accuracy, latency, memory usage, etc.) with a specific piece of code or a system. This metric is then usually used to compare different implementations of the same functionality in the hopes to improve the metric over time. This is especially important in the context of machine learning systems when measuring functional capabilities on specific tasks.

To accomplish measuring machine learning systems capabilities, in the context of the `nearai` project, we provide a benchmark tool to compare different agents and solvers on sets of reference evaluations. This tool enables you to do measurement and compare your systems on various sets of reference evaluations, ex: [`mpbb`](https://paperswithcode.com/dataset/mbpp). The core metric for benchmarks like these is "percent true" or *"accuracy"*.

## How is a benchmark implemented?

In the `nearai` project, a benchmark is the combination of a dataset and a solver.

### Adding a benchmark dataset

`nearai` leverages [huggingface datasets](https://huggingface.co/docs/datasets/en/index) as the primitive when operating with datasets + benchmarks (see [`load_dataset`](api.md#nearai.dataset.load_dataset)). This means that to add a new benchmark, you need to create a new dataset and register it with the `nearai` registry (we will go over this in [Implementing the "3 digit addition" benchmark](#implementing-the-3-digit-addition-benchmark)).

### Adding a solver

To implement a solver, you will need to implement the [SolverStrategy](api.md#nearai.solvers.SolverStrategy) interface under the [`nearai.solvers`](api.md#nearai.solvers) module. The most important method the solver should implement is the [`solve`](api.md#nearai.solvers.SolverStrategy.solve) method. This method should take a datum, run your implementation specific agentic strategy / strategies, and return a result.

## Implementing the "3 digit addition" benchmark

In this section we will be implementing a benchmark we'll call "3 digit addition". The goal of the benchmark is to test an agents ability to add two 1-3 digit numbers together. The dataset will consist of 1000 examples of 3 digit addition problems and their solutions. The solver will adjudicate the agents answers and return an single accuracy score. While this benchmark is simple and can be solved with a simple program, it serves as a good example of how to implement a benchmark in `nearai`.

### Step 1: Creating the dataset

To create this dataset, we will first synthetically generate the data. We will then register the dataset with the `nearai` registry.

```python
import random
from itertools import product

import datasets

SAMPLE_SIZE = 1000
SEED = 42
PATH = "3_digit_addition"

random.seed(SEED)
datasets.Dataset.from_generator(
    lambda: iter(
        {
            "input": f"{a} + {b}",
            "output": str(a + b)
        }
        for a, b in random.sample(list(product(range(1000), range(1000))), SAMPLE_SIZE)
    ),
    features=datasets.Features(
        {
            "input": datasets.Value("string"),
            "output": datasets.Value("string")
        }
    )
).save_to_disk(PATH)
```

Now to upload the dataset to the registry we'll run the command:

```bash
nearai registry upload ./3_digit_addition
```

### Step 2: Creating the solver

To create the solver, we will implement the `SolverStrategy` interface. The solver will take in a datum, parse the input, execute any setup for the agent, run the agent, and return the correctness of the agents result.

???+ note "Remember"
    To ensure this solver is registered with `nearai`:
    
    1. Write this implementation in the [`nearai.solvers`](api.md#nearai.solvers) module.
    2. Import it in the `__init__.py` file in the [`nearai.solvers`](api.md#nearai.solvers) module.

```python
# ... other imports ...
from pydantic import BaseModel
from huggingface import Dataset
from nearai.solvers import SolverStrategy

from typing import Dict, List

class ThreeDigitAdditionDatum(BaseModel):
    input: str
    output: str

class ThreeDigitAdditionAgentSolver(SolverStrategy):
    """Solver for the 3 digit addition benchmark."""

    def __init__(self, dataset_ref: Dataset, agent: str):
        self.dataset = dataset_ref
        self.agent = agent
        self.verbose = verbose
    
    def compatible_datasets(self) -> List[str]:
        return ["3_digit_addition"]

    def solve(self, datum: Dict[str, str]) -> bool:
        datum = ThreeDigitAdditionDatum(**datum)
        label = datum.input.replace(" + ", "+")
        path = os.path.join(
            "/tmp",
            "3_digit_addition",
            str(label),
            str(int(time.time() * 1000)),
            str(random.randint(0, 1000)),
        )
        CONFIG.confirm_commands = False
        env = Environment(path, [self.agent], CONFIG)

        goal = f"""Please add the following numbers together: {datum.input}\n\nOutput the result in a file called 'result.txt'."""
        env.run_task(goal)

        with open(os.path.join(path, "result.txt"), "r") as f:
            result = f.read().strip()
        return result == datum.output
```

### Step 3: Running the benchmark

To run the benchmark, we will use the `nearai` CLI. We will specify the dataset and solver we want to use.

```bash
nearai benchmark run 3_digit_addition ThreeDigitAdditionAgentSolver --agent <my_agent>
```
