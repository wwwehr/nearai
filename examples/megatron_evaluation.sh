TASK="LAMBADA"

wget https://raw.githubusercontent.com/cybertronai/bflm/master/lambada_test.jsonl lambada_test.jsonl
VALID_DATA=lambada_test.jsonl
VOCAB_FILE=~/.jasnah/models/gpt2-vocab.json/gpt2-vocab.json
MERGE_FILE=~/.jasnah/models/gpt2-merges.txt/gpt2-merges.txt
CHECKPOINT_PATH=~/.jasnah/checkpoints/gpt2_345m

COMMON_TASK_ARGS="--num-layers 24 \
                  --hidden-size 1024 \
                  --num-attention-heads 16 \
                  --seq-length 1024 \
                  --max-position-embeddings 1024 \
                  --fp16 \
                  --vocab-file $VOCAB_FILE"

export CUDA_DEVICE_MAX_CONNECTIONS=1
export MASTER_ADDR=localhost
export MASTER_PORT=6000

python third_party/Megatron-LM/tasks/main.py \
       --task $TASK \
       $COMMON_TASK_ARGS \
       --valid-data $VALID_DATA \
       --tokenizer-type GPT2BPETokenizer \
       --strict-lambada \
       --merge-file $MERGE_FILE \
       --load $CHECKPOINT_PATH \
       --micro-batch-size 8 \
       --log-interval 10 \
       --no-load-optim \
       --no-load-rng