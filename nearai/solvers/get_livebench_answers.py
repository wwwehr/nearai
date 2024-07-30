import argparse
import json
import os
import time
import glob

import shortuuid
from tqdm import tqdm
from nearai.config import CONFIG
from nearai.completion import InferenceRouter


class LiveBenchSolver:
    def __init__(self, model_path, model_id):
        self.model = model_path
        self.model_id = model_id
        self.completion_fn = InferenceRouter(CONFIG.llm_config).completions

    def solve(self, question):
        num_choices = 1
        choices = []
        for i in range(num_choices):
            conv = []
            # append system prompt?
            turns = []
            for qs in question["turns"]:
                conv.append({"role": "user", "content": qs})
                
                completion_response = self.completion_fn(
                    self.model,
                    conv,
                    temperature=0.0,
                    n=1,
                    stop=["<|eot_id|>"],
                )
                output = str(completion_response.choices[0].message.content)
                
                conv.append({"role": "assistant", "content": output})
                turns.append(output)

            choices.append({"index": i, "turns": turns})
        return choices


def run_eval(solver, questions, answer_file):
    answer_file = os.path.expanduser(answer_file)
    for question in tqdm(questions):
        choices = solver.solve(question)

        ans_json = {
            "question_id": question["question_id"],
            "answer_id": shortuuid.uuid(),
            "model_id": solver.model_id,
            "choices": choices,
            "tstamp": time.time(),
        }

        os.makedirs(os.path.dirname(answer_file), exist_ok=True)
        with open(answer_file, "a") as fout:
            fout.write(json.dumps(ans_json) + "\n")


def load_questions_jsonl(question_file: str):
    questions = []
    with open(question_file, "r") as ques_file:
        for line in ques_file:
            if line:
                questions.append(json.loads(line))
    return questions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--model-id", type=str, required=True)
    parser.add_argument("--bench-name", type=str, default="live_bench")

    args = parser.parse_args()

    solver = LiveBenchSolver(args.model_path, args.model_id)

    list_of_question_files = glob.glob(f"/home/setup/live_bench/**/question.jsonl", recursive=True)
    for question_file in list_of_question_files:
        print(question_file)
        questions = load_questions_jsonl(question_file)
        bench_name = os.path.dirname(question_file).replace("data/", "")
        bench_name = os.path.dirname(question_file).replace("/home/setup/", "")
        answer_file = f"~/data/{bench_name}/model_answer/{args.model_id}.jsonl"
        print(f"Questions from {question_file}")
        print(f"Output to {answer_file}")
        run_eval(solver, questions, answer_file)
