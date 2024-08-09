# Near AI

See the [Near AI website](https://near.ai) for more information about how we will achieve _Open Source and User-owned AGI._.

# ⚠️ Warning: Alpha software

NearAI is alpha software. This means that it is not yet ready for production use. We are actively working on improving the software and would love your help.

If you would like to help build our future, please see our [contributing guide](contributing.md).

# About

The NearAI project is a toolkit to help build, measure, and deploy AI systems focused on agents.

NearAI constists of:

1. A CLI tool to interact with the NearAI registry, download agents, run them in environments, and more.
2. A library with access to the same tools as the CLI, but to be used programmatically.
3. `nearai` hub, a place to share agents, environments, and datasets.

# Getting started

## Benchmarking

`nearai` includes a benchmarking tool to compare different agents and solvers on sets of reference evals (like [`mpbb`](https://paperswithcode.com/dataset/mbpp)).

???+ note "Requirements for benchmarking with `nearai`"
    To create a benchmark, you need two things:

    1. A dataset in your `nearai` dataset registry.
    2. A solver for the dataset implemented in the `nearai` library for said dataset.

    If you have a dataset and a solver, you can run a benchmark.

To run a benchmark, you can use the `nearai benchmark` command. For example, to run the `mpbb` benchmark on the `llama-v3-70b-instruct`, you can use:

```bash
nearai benchmark run mbpp MBPPSolverStrategy \
    --model llama-v3-70b-instruct \
    --subset=train \
    --max_concurrent=1
```

### Submit an experiment

To submit a new experiment run:

```
nearai submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as nearai are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `nearai.CONFIG.supervisor_id`. See [examples/prepare_data.py](examples/prepare_data.py) for an example.

### Registry

Upload an element to the registry using:

```
nearai registry upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

- The local path could be either to a file or a folder.
- The S3 path should be a non-existent folder in the registry.
- Tags is a comma separated list of tags to add to the item. This allows filtering relevant items.

There are two shortcuts to upload models and datasets. The following commands behave in the same way as `registry upload` but it adds by default the tags `model` and `dataset` respectively.

```
nearai models upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
nearai datasets upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

We recommend as a good practice to use as s3_path `@namespace/@name/@version`, but it is not mandatory.

### Fine tuning

We use [`torchtune`](https://github.com/pytorch/torchtune) to fine tuning models. The following command will start a fine tuning process using the `llama-3-8b-instruct` model and the `llama3` tokenizer.

```bash
poetry run python3 -m nearai finetune start \
    --model llama-3-8b-instruct \
    --format llama3-8b \
    --tokenizer tokenizers/llama-3 \
    --dataset <your-dataset> \
    --method nearai.finetune.text_completion.dataset \
    --column text \
    --split train \
    --num_procs 8
```
