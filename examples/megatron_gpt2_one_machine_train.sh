#! /bin/bash

# Starts or continues the "345M" parameter model.

RANK=0
WORLD_SIZE=1

DATA_PATH=~/.jasnah/datasets/school_math_ru/transformed/v0/training_data_text_document
CHECKPOINT_PATH=~/.jasnah/checkpoints/gpt2_345m
VOCAB_FILE=~/.jasnah/models/gpt2-vocab.json/gpt2-vocab.json
MERGE_FILE=~/.jasnah/models/gpt2-merges.txt/gpt2-merges.txt
export CUDA_DEVICE_MAX_CONNECTIONS=1
export MASTER_ADDR=localhost
export MASTER_PORT=6000


python third_party/Megatron-LM/pretrain_gpt.py \
       --num-layers 24 \
       --hidden-size 1024 \
       --num-attention-heads 16 \
       --micro-batch-size 4 \
       --global-batch-size 8 \
       --seq-length 1024 \
       --max-position-embeddings 1024 \
       --train-iters 500000 \
       --lr-decay-iters 320000 \
       --save $CHECKPOINT_PATH \
       --load $CHECKPOINT_PATH \
       --data-path $DATA_PATH \
       --vocab-file $VOCAB_FILE \
       --merge-file $MERGE_FILE \
       --data-impl mmap \
       --split 949,50,1 \
       --distributed-backend nccl \
       --lr 0.00015 \
       --min-lr 1.0e-5 \
       --lr-decay-style cosine \
       --weight-decay 1e-2 \
       --clip-grad 1.0 \
       --lr-warmup-fraction .01 \
       --log-interval 100 \
       --save-interval 10000 \
       --eval-interval 1000 \
       --eval-iters 10 \
       --fp16
