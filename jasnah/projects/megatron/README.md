# Megatron

## Setup

### Install Apex

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

### Install/fix dependencies

```
pip install --user -U nltk
pip uninstall torchvision
pip install torchvision --no-cache-dir
pip install torch --upgrade
pip install pybind11
pip install Ninja
```

### Install TransformerEngine

```
cd ~
git clone --branch stable --recursive https://github.com/NVIDIA/TransformerEngine.git
cd TransformerEngine
export NVTE_FRAMEWORK=pytorch
pip install .
```

Will take about ~10 min.

### Continue with project installation

```
cd ~/<path_to_project>/jasnah-cli/third_party/Megatron-LM
python3 -m pip install -e .
```

### Troubleshooting

#### Empty folder third_party/Megatron-LM

Checkout the branch without Megatron-LM dependency, run `git submodule add git@github.com:nearai/Megatron-LM.git third_party/Megatron-LM`, then checkout the branch with Megatron-LM dependency.

#### TransformerEngine installation takes too long

TransformerEngine installation is supposed to take ~10 min, and appears to be dependent on [install/fix dependencies](#installfix-dependencies). The installation process is different if `Ninja` is installed.

There is a Megatron fork not dependent on TransformerEngine: [Megatron for Megablocks](https://github.com/stanford-futuredata/Megatron-LM/tree/3a9e3d8de308e6f6398b59d16a8bd7177374f121), [nearai fork](https://github.com/nearai/Megatron-LM-for-MegaBlocks)

## Megatron functions

Run from a project root.

### Data preparation

The input training data should be in a loose json format, with one json containing a text sample per line in a 'text' field. All other fields are ignored.

[from_math_ds_to_training_json.py](from_math_ds_to_training_json.py) is an example script to convert math dataset into `training_data.json`.

Data preprocessing is specific for model. [preprocess_data_for_gpt2.py](preprocess_data_for_gpt2.py) is preprocessing example data for GPT2 model.

### Training

[gpt2_one_machine_train.sh](gpt2_one_machine_train.sh) is an example script to start or continue training on one machine.

The `third_party/Megatron-LM/examples/pretrain_{bert,gpt,t5}_distributed.sh` scripts use the PyTorch distributed launcher for distributed training.

`third_party/Megatron-LM/examples/pretrain_gpt3_175B.sh` is an example of how to configure Megatron to run GPT-3 with 175 billion parameters on 1024 GPUs.

### Finetuning

Finetuning in Megatron is the same process as pretraining. The `--finetune` arg is used to reset training parameters and start finetuning. [gpt2_one_machine_finetune.sh](gpt2_one_machine_finetune.sh) is an example script to start finetuning on one machine.

### Change parameters of the model (for inference)

To change parameters of the model:

```
python tools/checkpoint/convert.py \
        --model-type GPT \
        --load-dir checkpoints/gpt3_tp4_pp4 \
        --save-dir checkpoints/gpt3_tp2_pp2 \
        --target-tensor-parallel-size 2 \
        --target-pipeline-parallel-size 2
```

### Megatron Inference Server

[inference_server.sh](inference_server.sh) contains a script to run a server using a model in checkpoints folder, and an example prompt.

### Megatron Evaluation Scripts

[lambada_evaluation.sh](lambada_evaluation.sh)
