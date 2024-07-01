from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Optional

from jasnah import timestamp
from jasnah.config import DATA_FOLDER
from jasnah.dataset import get_dataset
from jasnah.model import get_model

# TODO: What do we want to log


class FinetuneCli:
    def submit(self):
        """Submit a finetuning job to the cluster"""
        raise NotImplementedError()

    def start(
        self,
        model: str,
        dataset: str,
        num_procs: int,
        num_nodes: int,
        job_id: Optional[str] = None,
        checkpoint: Optional[str] = None,
        epochs: int = 1,
        rank: int = -1,
        master_addr: Optional[str] = None,
    ):
        """Start a finetuning job on the current node"""

        if job_id is None:
            job_id = timestamp()

        assert num_nodes >= 1

        model_path = get_model(model)

        if checkpoint:
            checkpoint_path = get_model(checkpoint)
        else:
            checkpoint_path = None

        dataset_path = get_dataset(dataset)

        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            with open(config, "w") as f:
                f.write(
                    CONFIG_TEMPLATE.format(
                        MODEL=None,
                        CHECKPOINT=None,
                        CHECKPOINT_OUTPUT=None,
                        LOGGING=None,
                    )
                )

        if num_nodes == 1:
            run(
                [
                    "tune",
                    "run",
                    "--nproc_per_node",
                    str(num_procs),
                    "lora_finetune_distributed",
                    "--config",
                    str(config)
                ]
            )
        else:
            raise NotImplementedError()

    def inspect(self, job_id: str):
        raise NotImplementedError()


# https://github.com/pytorch/torchtune/blob/main/recipes/configs/llama3/70B_lora.yaml
CONFIG_TEMPLATE = """
# Config for multi-device LoRA in lora_finetune_distributed.py
# using a Llama3 70B model
#
# This config assumes that you've run the following command before launching
# this run:
#   tune download meta-llama/Meta-Llama-3-70B-Instruct --hf-token <TOKEN> --output-dir /tmp/Meta-Llama-3-70B-Instruct --ignore-patterns "original/consolidated*"
#
# This config needs 8 GPUs to run
#   # tune run --nproc_per_node 8 lora_finetune_distributed --config llama3/70B_lora
#

# Model Arguments
model:
  _component_: torchtune.models.llama3.lora_llama3_70b
  lora_attn_modules: ['q_proj', 'k_proj', 'v_proj']
  apply_lora_to_mlp: False
  apply_lora_to_output: False
  lora_rank: 16
  lora_alpha: 32

tokenizer:
  _component_: torchtune.models.llama3.llama3_tokenizer
  path: {MODEL}

checkpointer:
  _component_: torchtune.utils.FullModelHFCheckpointer
  checkpoint_dir: {MODEL}
  checkpoint_files: [
    model-00001-of-00030.safetensors,
    model-00002-of-00030.safetensors,
    model-00003-of-00030.safetensors,
    model-00004-of-00030.safetensors,
    model-00005-of-00030.safetensors,
    model-00006-of-00030.safetensors,
    model-00007-of-00030.safetensors,
    model-00008-of-00030.safetensors,
    model-00009-of-00030.safetensors,
    model-00010-of-00030.safetensors,
    model-00011-of-00030.safetensors,
    model-00012-of-00030.safetensors,
    model-00013-of-00030.safetensors,
    model-00014-of-00030.safetensors,
    model-00015-of-00030.safetensors,
    model-00016-of-00030.safetensors,
    model-00017-of-00030.safetensors,
    model-00018-of-00030.safetensors,
    model-00019-of-00030.safetensors,
    model-00020-of-00030.safetensors,
    model-00021-of-00030.safetensors,
    model-00022-of-00030.safetensors,
    model-00023-of-00030.safetensors,
    model-00024-of-00030.safetensors,
    model-00025-of-00030.safetensors,
    model-00026-of-00030.safetensors,
    model-00027-of-00030.safetensors,
    model-00028-of-00030.safetensors,
    model-00029-of-00030.safetensors,
    model-00030-of-00030.safetensors,
  ]
  recipe_checkpoint: {CHECKPOINT}
  output_dir: {CHECKPOINT_OUTPUT}
  model_type: LLAMA3
resume_from_checkpoint: False

# Dataset and Sampler
dataset:
  _component_: torchtune.datasets.alpaca_dataset
seed: null
shuffle: True
batch_size: 2

# Optimizer and Scheduler
optimizer:
  _component_: torch.optim.AdamW
  weight_decay: 0.01
  lr: 3e-4
lr_scheduler:
  _component_: torchtune.modules.get_cosine_schedule_with_warmup
  num_warmup_steps: 100

loss:
  _component_: torch.nn.CrossEntropyLoss

# Training
epochs: 1
max_steps_per_epoch: null
gradient_accumulation_steps: 1

# Logging
output_dir: {LOGGING}
metric_logger:
  _component_: torchtune.utils.metric_logging.DiskLogger
  log_dir: ${{output_dir}}
log_every_n_steps: 1
log_peak_memory_stats: False

# Environment
device: cuda
dtype: bf16
enable_activation_checkpointing: True
"""
