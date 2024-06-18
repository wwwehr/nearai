#! /bin/bash

# Converts llama model to nemo model.
#
# Run from a project root.

MODEL_INPUT_PATH='/root/.jasnah/registry/models/llama-3-8b'
MODEL_OUTPUT_PATH='/root/.jasnah/registry/models/llama-3-8b.nemo'

CMD="cd /NeMo && python scripts/checkpoint_converters/convert_llama_hf_to_nemo.py --input_name_or_path=$MODEL_INPUT_PATH --output_path=$MODEL_OUTPUT_PATH"

sudo docker run --gpus device=1 --shm-size=2g --net=host --ulimit memlock=-1 --rm -it \
    -v $(pwd)/third_party/NeMo:/NeMo \
    -v ~/.jasnah/registry/models:/root/.jasnah/registry/models \
    nvcr.io/nvidia/nemo:24.05 \
    /bin/bash -c "$CMD"