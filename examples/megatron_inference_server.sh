#!/bin/bash
# This example will start serving the 345M model.
# Example prompt:
# curl 'http://localhost:5000/api' -X 'PUT' -H 'Content-Type: application/json; charset=UTF-8'  -d '{"prompts":["<problem>2+5</problem><answer>"], "tokens_to_generate":10}'
DISTRIBUTED_ARGS="--nproc_per_node 1 \
                  --nnodes 1 \
                  --node_rank 0 \
                  --master_addr localhost \
                  --master_port 6000"

# CHECKPOINT=~/.jasnah/checkpoints/gpt2_345m
CHECKPOINT=third_party/Megatron-LM/checkpoints/gpt2_345m
VOCAB_FILE=~/.jasnah/models/gpt2-vocab.json/gpt2-vocab.json
MERGE_FILE=~/.jasnah/models/gpt2-merges.txt/gpt2-merges.txt

pip install flask-restful

export CUDA_DEVICE_MAX_CONNECTIONS=1

python -m torch.distributed.run $DISTRIBUTED_ARGS third_party/Megatron-LM/tools/run_text_generation_server.py   \
       --tensor-model-parallel-size 1  \
       --pipeline-model-parallel-size 1  \
       --num-layers 24  \
       --hidden-size 1024  \
       --load ${CHECKPOINT}  \
       --num-attention-heads 16  \
       --max-position-embeddings 1024  \
       --tokenizer-type GPT2BPETokenizer  \
       --fp16  \
       --micro-batch-size 1  \
       --seq-length 1024  \
       --out-seq-length 1024  \
       --temperature 1.0  \
       --vocab-file $VOCAB_FILE  \
       --merge-file $MERGE_FILE  \
       --top_p 0.9  \
       --seed 42
