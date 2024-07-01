import os
import random
import time

from typing import List, Union
from datasets import Dataset, DatasetDict

from jasnah.config import CONFIG
from jasnah.solvers import SolverStrategy
from jasnah.solvers.mbpp_solver import MBPPDatum
from jasnah.agent import load_agent
from jasnah.environment import Environment


class MBPPSolverAgent(SolverStrategy):
    """
    Solver strategy for the MBPP dataset
    """

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], agent, num_iterations=16, verbose=False):
        super().__init__()
        self.dataset_ref = dataset_ref
        self.agent = load_agent(agent)
        self.verbose = verbose
        self.num_iterations = num_iterations

    def compatible_datasets(self) -> List[str]:
        return ["mbpp"]

    def solve(self, datum: dict) -> bool:
        print(datum)
        datum = MBPPDatum(**datum)

        path = os.path.join('/tmp', str(int(time.time() * 1000)), str(random.randint(0, 1000)), 'mbpp', str(datum.task_id))
        CONFIG.llm_config['confirm_commands'] = False
        env = Environment(path, [self.agent], CONFIG.llm_config)

        new_line = '\n'
        task = f"{datum.text}\nIt should pass next tests:\n```python\n{new_line.join(datum.test_list)}\n```"
        if self.verbose:
            print(task)
            print(path)
        env.run_task(task, max_iterations=self.num_iterations)

        code = ""
        for filename in env.list_files('.'):
            if filename.endswith('.py'):
                code += env.read_file(filename) + '\n'

        try:
            for test in datum.test_list + datum.challenge_test_list:
                test_code = code + "\n" + test
                exec(test_code)
            return True
        except Exception as e:
            if self.verbose:
                print(e)
            return False
