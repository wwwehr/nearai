# Megatron

## Setup

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
```

```
     if (bare_metal_version != torch_binary_version):
+
+        # allow minor version mismatch
+        if bare_metal_version.major == torch_binary_version.major and bare_metal_version.minor != torch_binary_version.minor:
+            return
+
         raise RuntimeError(
             "Cuda extensions are being compiled with a version of Cuda that does "
             "not match the version used to compile Pytorch binaries.  "
```

Try installing again:

```
pip install -v --disable-pip-version-check --no-cache-dir --no-build-isolation --config-settings "--build-option=--cpp_ext" --config-settings "--build-option=--cuda_ext" ./
```

### Continue installation

```
cd ~/<path_to_project>/jasnah-cli/third_party/Megatron-LM
python3 -m pip install -e .
```

## Megatron functions

### Data preparation

The input training data should be in a loose json format, with one json containing a text sample per line in a 'text' field. All other fields are ignored.

[from_math_ds_to_training_json.py](from_math_ds_to_training_json.py) is an example script to convert math dataset into `training_data.json`.

Data preprocessing is specific for model. [preprocess_data_for_gpt2.py](preprocess_data_for_gpt2.py) is preprocessing example data for GPT2 model.

### Training

[examples/megatron_gpt2_one_machine_train.sh](examples/megatron_gpt2_one_machine_train.sh) is an example script to start or continue training on one machine.

The `third_party/Megatron-LM/examples/pretrain_{bert,gpt,t5}_distributed.sh` scripts use the PyTorch distributed launcher for distributed training.

[third_party/Megatron-LM/examples/pretrain_gpt3_175B.sh](third_party/Megatron-LM/examples/pretrain_gpt3_175B.sh) is an example of how to configure Megatron to run GPT-3 with 175 billion parameters on 1024 GPUs.

### Finetuning

Finetuning in Megatron is the same process as pretraining. The `--finetune` arg is used to reset training parameters and start finetuning. [examples/megatron_gpt2_one_machine_finetune.sh](examples/megatron_gpt2_one_machine_finetune.sh) is an example script to start finetuning on one machine.

### Checkpoint_util

To change parameters of the model:
```
python third_party/Megatron-LM/tools/checkpoint_util.py \
        --model-type GPT \
        --load-dir checkpoints/gpt3_tp4_pp4 \
        --save-dir checkpoints/gpt3_tp2_pp2 \
        --target-tensor-parallel-size 2 \
        --target-pipeline-parallel-size 2
```

### Megatron Inference Server

[examples/megatron_inference_server.sh](examples/megatron_inference_server.sh) contains a script to run a server using a model in checkpoints folder, and an example prompt.

### Megatron Evaluation Scripts

[examples/megatron_evaluation.sh](examples/megatron_evaluation.sh)
