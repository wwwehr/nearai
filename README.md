# Jasnah CLI

## Setup

First install jasnah-cli by running:

```
git clone jasnah-cli
cd jasnah-cli
python3 -m pip install -e .
pip install openai
```

Check the installation worked with

```
jasnah-cli version
```

Setup basic configuration

```
jasnah-cli config set db_user <DB_USERNAME>
jasnah-cli config set db_password <DB_PASSWORD>
jasnah-cli config set user_name <YOUR_NAME>
```

The user name will be used to identify the author of the experiments.
This configuration can be manually edited at `~/.jasnah/config.json`, or per project at `.jasnah/config.json` (relative to the current directory).

To use the registry (for downloading and uploading models and datasets) you need to setup access to S3. Do it by installing [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) and configuring it:

```
export AWS_ACCESS_KEY_ID=<..>
export AWS_SECRET_ACCESS_KEY="<..>"
```

### Install Apex for Megatron

```
cd ~
git clone https://github.com/NVIDIA/apex
cd apex
pip install -v --disable-pip-version-check --no-cache-dir --no-build-isolation --config-settings "--build-option=--cpp_ext" --config-settings "--build-option=--cuda_ext" ./
```

If version mismatch, edit `setup.py`:

```
nano setup.py
pip install -v --disable-pip-version-check --no-cache-dir --no-build-isolation --config-settings "--build-option=--cpp_ext" --config-settings "--build-option=--cuda_ext" ./
```

## Update

To update jasnah-cli run:

```
# Go to the jasnah-cli folder
cd jasnah-cli

git pull

# The next step is only required in case some dependencies were added or updated, otherwise pulling new changes is enough
python3 -m pip install -e .
```

## Usage

### Submit an experiment

To submit a new experiment run:

```
jasnah-cli submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as jasnah-cli are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `jasnah.CONFIG.supervisor_id`. See [examples/prepare_data.py](examples/prepare_data.py) for an example.

### Registry

Upload a new dataset or model to the registry:

```
jasnah-cli models upload <PATH_TO_MODEL> <MODEL_NAME> <DESCRIPTION> [--alias <ALIAS>]
jasnah-cli datasets upload <PATH_TO_DATASET> <DATASET_NAME> <DESCRIPTION> [--alias <ALIAS>]
```

The path could be either to a file or a folder.
The name is a unique identifier, and the alias is a human readable name that can be used to refer to the model or dataset.

### Megatron functions

#### Data preparation

The input training data should be in a loose json format, with one json containing a text sample per line in a 'text' field. All other fields are ignored.

[examples/from_math_ds_to_training_json.py](examples/from_math_ds_to_training_json.py) is an example script to convert math dataset into `training_data.json`.

Data preprocessing is specific for model. [examples/preprocess_data_for_gpt2.py](examples/preprocess_data_for_gpt2.py) is preprocessing example data for GPT2 model.

#### Training

[examples/megatron_gpt2_one_machine_train.sh](examples/megatron_gpt2_one_machine_train.sh) is an example script to start or continue training on one machine.

The `third_party/Megatron-LM/examples/pretrain_{bert,gpt,t5}_distributed.sh` scripts use the PyTorch distributed launcher for distributed training.

[third_party/Megatron-LM/examples/pretrain_gpt3_175B.sh](third_party/Megatron-LM/examples/pretrain_gpt3_175B.sh) is an example of how to configure Megatron to run GPT-3 with 175 billion parameters on 1024 GPUs.

#### Finetuning

Finetuning in Megatron is the same process as pretraining. The `--finetune` arg is used to reset training parameters and start finetuning. [examples/megatron_gpt2_one_machine_finetune.sh](examples/megatron_gpt2_one_machine_finetune.sh) is an example script to start finetuning on one machine.

#### Checkpoint_util

To change parameters of the model:
```
python third_party/Megatron-LM/tools/checkpoint_util.py \
        --model-type GPT \
        --load-dir checkpoints/gpt3_tp4_pp4 \
        --save-dir checkpoints/gpt3_tp2_pp2 \
        --target-tensor-parallel-size 2 \
        --target-pipeline-parallel-size 2
```

#### Megatron Inference Server

[examples/megatron_inference_server.sh](examples/megatron_inference_server.sh) contains a script to run a server using a model in checkpoints folder, and an example prompt.

#### Megatron Evaluation Scripts

[examples/megatron_evaluation.sh](examples/megatron_evaluation.sh)

### Library

You can import `jasnah` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
- Store log events in the database. TODO Example.
- Fetch information about running or past experiments. TODO Example.
