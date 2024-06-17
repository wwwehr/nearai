#! /bin/bash

# Training or finetuning a model.
#
# Run from a project root.

MODEL_PATH='/root/.jasnah/registry/models/llama-3-8b.nemo'

CMD="cd /NeMo python scripts/checkpoint_converters/convert_llama_hf_to_nemo.py --input_name_or_path=$MODEL_INPUT_PATH --output_path=$MODEL_OUTPUT_PATH"
APEX_INSTALL="cd /root/.jasnah/nemo_dependencies/apex && pip install . -v --no-build-isolation --disable-pip-version-check --no-cache-dir --config-settings \"--build-option=--cpp_ext --cuda_ext --fast_layer_norm --distributed_adam --deprecated_fused_adam --group_norm\""

sudo docker run --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 --rm -it \
    -v $(pwd)/third_party/NeMo:/NeMo \
    -v ~/.jasnah/checkpoints:/root/.jasnah/checkpoints \
    -v ~/.jasnah/registry/models:/root/.jasnah/registry/models \
    -v ~/.jasnah/registry/datasets:/root/.jasnah/registry/datasets \
    -v ~/.jasnah/nemo_dependencies:/root/.jasnah/nemo_dependencies \
    nvcr.io/nvidia/nemo:24.05 \
    /bin/bash -c "$APEX_INSTALL && $CMD"