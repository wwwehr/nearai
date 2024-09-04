

```python
from textwrap import dedent
from datasets import load_dataset
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B-Instruct")


ds = load_dataset("HuggingFaceH4/orca-math-word-problems-200k")

## create new column by concatenating the 'question' and 'answer' columns
def to_q_a(x):
    q_n_a = tokenizer.apply_chat_template(
        [
            {
                "role": "system",
                "content": "You are a helpful assistant. Please answer the math question."
            },
            {
                "role": "user",
                "content": x["question"]
            },
            {
                "role": "assistant",
                "content": x["answer"]
            }
        ],
        tokenize=False
    )
    return {
        "question_and_answer": q_n_a
    }
ds = ds.map(to_q_a)
ds.save_to_disk("orca_math")
```

```bash
poetry run python3 -m nearai finetune start \
    --model llama-3-8b-instruct \
    --format llama3-8b \
    --tokenizer llama-3-8b-instruct/tokenizer.model \
    --dataset ./orca_math/ \
    --method nearai.finetune.text_completion.dataset \
    --column question_and_answer \
    --split train_sft \
    --num_procs 8
```

```
/home/user/.nearai/finetune/job-2024-08-29_20-58-08-207756662/checkpoint_output
```

serve via vllm

```
poetry run python3 -m vllm.entrypoints.openai.api_server \
    --host 0.0.0.0 \
    --port 9090 \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --enable-lora \
    --lora-modules prog=/home/user/.nearai/finetune/job-2024-08-29_20-58-08-207756662/checkpoint_output/ \
    --tensor-parallel 4
```


benchmark dataset 

```python
from datasets import load_dataset
ds = load_dataset("openai/gsm8k", "main")
def exract_answer(x):
    raw_answer = x["answer"]
    parsed_answer = raw_answer.split("####")[1].strip()
    return {
        "answer": parsed_answer
    }
ds = ds.map(exract_answer)
ds.save_to_disk("gsm8k")
```

```sh
poetry run python3 -m nearai benchmark run \
    gsm8k \
    GSM8KSolverStrategy \
    --subset test \
    --model prog
    --model meta-llama/Meta-Llama-3-8B-Instruct
```

# meta-llama/Meta-Llama-3-8B-Instruct
Correct/Seen - 942/1319 - 71.42% # prompt 1
Correct/Seen - 942/1319 - 71.87% # prompt 2

# fine tuned llama3-8b-instruct
# fine tune orca-math-word-problems-200k
Correct/Seen - 748/1319 - 56.71% # prompt 1
Correct/Seen - 926/1319 - 70.20% # prompt 2
