# NeMo

## Setup

It is recommended to use a Docker container `nvcr.io/nvidia/nemo:24.05` which comes with all the setup environment.

### Troubleshooting

#### Empty folder third_party/NeMo

```
git submodule init
git submodule update
```

#### Apex errors

https://github.com/NVIDIA/apex/issues/1803

Download Apex for use in Docker
```
mkdir ~/.jasnah/nemo_dependencies
cd ~/.jasnah/nemo_dependencies
sudo git clone https://github.com/NVIDIA/apex
cd apex
sudo git checkout 810ffae374a2b9cb4b5c5e28eaeca7d7998fca0c
```

Add Apex installation to docker runs:
```
APEX_INSTALL="cd /root/.jasnah/nemo_dependencies/apex && pip install . -v --no-build-isolation --disable-pip-version-check --no-cache-dir --config-settings \"--build-option=--cpp_ext --cuda_ext --fast_layer_norm --distributed_adam --deprecated_fused_adam --group_norm\""

sudo docker run --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 --rm -it \
    -v $(pwd)/third_party/NeMo:/NeMo \
    -v ~/.jasnah/checkpoints:/root/.jasnah/checkpoints \
    -v ~/.jasnah/registry/models:/root/.jasnah/registry/models \
    -v ~/.jasnah/registry/datasets:/root/.jasnah/registry/datasets \
    -v ~/.jasnah/nemo_dependencies:/root/.jasnah/nemo_dependencies \
    nvcr.io/nvidia/nemo:24.05 \
    /bin/bash -c "$APEX_INSTALL && $CMD"
```

## NeMo functions

Run from a project root.

### Data preparation (text)

The expected format is a JSONL file with {‘input’: ‘xxx’, ‘output’: ‘yyy’} pairs.

[from_math_ds_to_training_json.py](from_math_ds_to_training_json.py) is an example script to convert math dataset into `training_data.json`.

### Convert model to .nemo

[convert_llama_to_nemo.sh](convert_llama_to_nemo.sh) converts llama huggingface models to `.nemo` models.

### Training / Finetuning

[llama_one_machine_finetune.sh](llama_one_machine_finetune.sh) is an example script to start or continue training on one machine.

### Evaluation

TODO