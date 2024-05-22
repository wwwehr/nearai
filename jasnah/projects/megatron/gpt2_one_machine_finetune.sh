#! /bin/bash

# Starts or continues the "345M" parameter model.
#
# Run from a project root.
#
# To continue finetuning:
# 1. Update BASE_PATH to be the same as FINETUNE_PATH.
# 2. Remove --finetune arg.

export CUDA_DEVICE_MAX_CONNECTIONS=1

BASE_PATH=~/.jasnah/checkpoints/gpt2_345m
FINETUNE_PATH=~/.jasnah/checkpoints/gpt2_345m_finetune
VOCAB_FILE=~/.jasnah/models/gpt-2-vocabulary/gpt2-vocab.json
MERGE_FILE=~/.jasnah/models/gpt-2-vocabulary/gpt2-merges.txt
DATA_PATH=~/.jasnah/datasets/school_math_ru/transformed/v0/training_data_text_document

GPT_ARGS="
    --num-layers 24 \
    --hidden-size 1024 \
    --num-attention-heads 16 \
    --seq-length 1024 \
    --max-position-embeddings 1024 \
    --micro-batch-size 4 \
    --global-batch-size 8 \
    --lr 0.00015 \
    --train-iters 500000 \
    --lr-decay-iters 320000 \
    --lr-decay-style cosine \
    --min-lr 1.0e-5 \
    --weight-decay 1e-2 \
    --lr-warmup-fraction .01 \
    --clip-grad 1.0 \
    --fp16
    --attention-softmax-in-fp32
    --finetune
"

DATA_ARGS="
    --data-path $DATA_PATH \
    --vocab-file $VOCAB_FILE \
    --merge-file $MERGE_FILE \
    --split 949,50,1
"

OUTPUT_ARGS="
    --log-interval 100 \
    --save-interval 10000 \
    --eval-interval 1000 \
    --eval-iters 10
"

torchrun third_party/Megatron-LM/pretrain_gpt.py \
    $GPT_ARGS \
    $DATA_ARGS \
    $OUTPUT_ARGS \
    --save $FINETUNE_PATH \
    --load $BASE_PATH
