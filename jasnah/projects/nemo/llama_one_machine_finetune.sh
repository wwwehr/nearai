#! /bin/bash

# Training or finetuning a model.
# Change the scheme of training (full, lora, etc) in `model.peft.peft_scheme` of RESUME_ARGS
#
# Run from a project root.
# `bash jasnah/projects/nemo/llama_one_machine_finetune.sh`

PATH_ARGS=(
    model.restore_from_path='/root/.jasnah/registry/models/llama-3-8b.nemo'
    model.data.train_ds.file_names="[/root/.jasnah/registry/datasets/school_math_ru/transformed/v0/training_data.json]"
    model.data.train_ds.concat_sampling_probabilities="[1]"
    model.data.validation_ds.file_names="[/root/.jasnah/registry/datasets/school_math_ru/transformed/v0/training_data.json]"
    model.data.test_ds.file_names="[/root/.jasnah/registry/datasets/school_math_ru/transformed/v0/training_data.json]"
    exp_manager.explicit_log_dir=/root/.jasnah/checkpoints/logs
)

DIST_ARGS=(
    --nproc_per_node=8
)

TOPOLOGY_ARGS=(
    model.tensor_model_parallel_size=2
    model.pipeline_model_parallel_size=4
)

# Use model.peft.peft_scheme=none for full training and model.peft.peft_scheme='lora' for lora.
RESUME_ARGS=(
    model.peft.peft_scheme=none
    exp_manager.resume_if_exists=True
    exp_manager.resume_ignore_no_checkpoint=True
)

ARGS=(
   trainer.precision=bf16
   trainer.devices=8
   trainer.num_nodes=1
   trainer.val_check_interval=0.1
   trainer.max_steps=50
   model.micro_batch_size=1
   model.global_batch_size=128
   model.megatron_amp_O2=True
   model.sequence_parallel=True
   model.activations_checkpoint_granularity=selective
   model.activations_checkpoint_method=uniform
   model.optim.name=fused_adam
   model.optim.lr=5e-6
   model.answer_only_loss=True
   model.data.train_ds.max_seq_length=2048
   model.data.validation_ds.max_seq_length=2048
   model.data.train_ds.micro_batch_size=1
   model.data.train_ds.global_batch_size=128
   model.data.validation_ds.micro_batch_size=1
   model.data.validation_ds.global_batch_size=128
   model.data.test_ds.micro_batch_size=1
   model.data.test_ds.global_batch_size=256
   model.data.train_ds.num_workers=0
   model.data.validation_ds.num_workers=0
   model.data.test_ds.num_workers=0
   model.data.validation_ds.metric.name=loss
   model.data.test_ds.metric.name=loss
   exp_manager.create_wandb_logger=False
   exp_manager.create_checkpoint_callback=True
   exp_manager.checkpoint_callback_params.monitor=validation_loss
   exp_manager.checkpoint_callback_params.save_best_model=False
   exp_manager.checkpoint_callback_params.save_nemo_on_train_end=True
   ++cluster_type=BCP
)

TORCHRUN_CMD="torchrun ${DIST_ARGS[@]} examples/nlp/language_modeling/tuning/megatron_gpt_finetuning.py ${ARGS[@]} ${PATH_ARGS[@]} ${TOPOLOGY_ARGS[@]} ${RESUME_ARGS[@]}"

CMD="cd /NeMo && $TORCHRUN_CMD"

sudo docker run --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 --rm -it \
    -v $(pwd)/third_party/NeMo:/NeMo \
    -v ~/.jasnah/checkpoints:/root/.jasnah/checkpoints \
    -v ~/.jasnah/registry/models:/root/.jasnah/registry/models \
    -v ~/.jasnah/registry/datasets:/root/.jasnah/registry/datasets \
    nvcr.io/nvidia/nemo:24.05 \
    /bin/bash -c "$CMD"