# NeMo

## Setup

It is recommended to use a Docker container `nvcr.io/nvidia/nemo:24.05`

### Download Apex for use in Docker

```
mkdir ~/.jasnah/nemo_dependencies
cd ~/.jasnah/nemo_dependencies
git clone https://github.com/NVIDIA/apex
cd apex
git checkout $810ffae374a2b9cb4b5c5e28eaeca7d7998fca0c
```

### Troubleshooting

#### Empty folder third_party/NeMo

```
git submodule init
git submodule update
```

## NeMo functions

Run from a project root.

### Data preparation (text)

The expected format is a JSONL file with {‘input’: ‘xxx’, ‘output’: ‘yyy’} pairs.

[from_math_ds_to_training_json.py](from_math_ds_to_training_json.py) is an example script to convert math dataset into `training_data.json`.

### Convert model to .nemo

[convert_llama_to_nemo.sh] converts llama huggingface models to `.nemo` models.

### Training / Finetuning

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
