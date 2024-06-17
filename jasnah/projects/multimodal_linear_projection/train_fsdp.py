import functools
import os
import subprocess as sp
from pathlib import Path

import datasets
import torch.distributed as dist
import torch.nn
from tensorboardX import SummaryWriter
from torch.distributed.device_mesh import init_device_mesh
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy
from torch.distributed.fsdp.wrap import size_based_auto_wrap_policy, transformer_auto_wrap_policy
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm
from transformers.models.llama.modeling_llama import LlamaConfig, LlamaDecoderLayer

import jasnah
import jasnah.dataset
import jasnah.model

from .multimodal import AutoTokenizer, ImageDescription, ImageTokenizer, LlamaMultimodalModel, MultimodalTokenizer

TOTAL_RANKS = int(os.getenv("WORLD_SIZE"))
LOCAL_RANK = int(os.getenv("LOCAL_RANK"))
RANK = int(os.getenv("RANK"))
LOCAL_WORLD_SIZE = int(os.getenv("LOCAL_WORLD_SIZE"))

CHECKPOINT_START = 1000
CHECKPOINT_INC = 2
CHECKPOINT_TOP = 180000
STATS_EVERY = 500

if LOCAL_RANK == 0:
    timestamp = jasnah.timestamp()
    writer = SummaryWriter(f"logdir/{timestamp}")

SEED = 42


def log(name, value, step):
    if LOCAL_RANK == 0:
        if isinstance(value, torch.Tensor) and value.dtype == torch.bfloat16:
            value = value.to(torch.float32)

        # print(f"{step}: {name} = {value}")
        writer.add_scalar(name, value, step)


def print_params_stats(params: torch.Tensor, prefix: str, step):
    log(f"{prefix}_norm1", params.abs().mean(), step)
    log(f"{prefix}_norm2", (params**2).mean().sqrt(), step)


def print_stats(model: LlamaMultimodalModel, step):
    linear = model.image_projection
    print_params_stats(linear.weight, "weight/", step)
    print_params_stats(linear.bias, "bias/", step)
    if linear.weight.grad is not None:
        print_params_stats(linear.weight.grad, "weight/grad", step)
        print_params_stats(linear.bias.grad, "bias/grad", step)


def summary(model: torch.nn.Module, print_params=True):
    trainable_params = 0
    all_params = 0
    for name, param in model.named_parameters():
        if param.requires_grad:
            if print_params:
                print(name, param.size())
            trainable_params += param.numel()
        all_params += param.numel()

    print("Trainable params:", trainable_params)
    print("All params:", all_params)


def checkpoint(model: LlamaMultimodalModel, samples: int):
    if RANK != 0:
        return

    folder = Path("checkpoints") / timestamp
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"model_{samples}.pt"
    torch.save(model.image_projection.state_dict(), path)


def my_policy(*args, **kwargs):
    return False


def get_gpu_memory():
    command = "nvidia-smi --query-gpu=memory.used --format=csv"
    memory_free_info = sp.check_output(command.split()).decode("ascii").split("\n")[:-1][1:]
    memory_free_values = [int(x.split()[0]) / 1024 for i, x in enumerate(memory_free_info)]
    return memory_free_values


def check_memory(msg=""):
    if LOCAL_RANK == 0:
        torch.cuda.synchronize()
        print(msg, get_gpu_memory())


def my_policy():
    return functools.partial(
        transformer_auto_wrap_policy,
        transformer_layer_cls={
            LlamaDecoderLayer,
        },
    )


def main():
    device = torch.device("cuda", LOCAL_RANK)
    torch.cuda.set_device(device)

    assert TOTAL_RANKS % LOCAL_WORLD_SIZE == 0
    device_mesh = init_device_mesh("cuda", (TOTAL_RANKS // LOCAL_WORLD_SIZE, LOCAL_WORLD_SIZE))

    model_path = jasnah.model.get_model("llama-3-8b-instruct")

    if LOCAL_RANK == 0:
        model = LlamaMultimodalModel.from_pretrained(model_path)
    else:
        llama_config = LlamaConfig.from_pretrained(model_path)
        llama_config.use_cache = False
        with torch.device("meta"):
            model = LlamaMultimodalModel(llama_config)

    model.to(torch.bfloat16)
    model.train()
    model.freeze_lang_model()

    if LOCAL_RANK == 0:
        print()
        print("Number of parameters (before FSDP)")
        summary(model, print_params=False)

        model.image_projection.to(device)

    else:
        model.image_projection.to_empty(device=device)

    model.image_projection.reset_parameters()

    dist.all_reduce(model.image_projection.weight.data, op=dist.ReduceOp.AVG)
    dist.all_reduce(model.image_projection.bias.data, op=dist.ReduceOp.AVG)

    if LOCAL_RANK == 0:
        print("Image projection weights and biases synchronized")

    model = FSDP(
        model,
        auto_wrap_policy=my_policy(),
        ignored_modules=[model.image_projection],
        sharding_strategy=ShardingStrategy.HYBRID_SHARD,
        device_id=LOCAL_RANK,
        device_mesh=device_mesh,
        sync_module_states=True,
        param_init_fn=lambda module: module.to_empty(device=device, recurse=False) if LOCAL_RANK != 0 else None,
    )

    if LOCAL_RANK == 0:
        print()
        print("Number of parameters (after FSDP)")
        summary(model, print_params=False)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    dataset_path = jasnah.dataset.get_dataset("ncimages_ru") / "descriptions"
    ds = datasets.DatasetDict.load_from_disk(str(dataset_path))
    train_ds = ds["train"]

    EPOCHS = 1
    BATCH_SIZE_PER_RANK = 4
    BATCH_SIZE = BATCH_SIZE_PER_RANK * TOTAL_RANKS

    pbar = tqdm(total=len(train_ds) * EPOCHS)

    n = len(train_ds)

    checkpoint(model.module, 0)
    next_checkpoint = CHECKPOINT_START
    next_stat = 0

    for epoch in range(EPOCHS):
        for batch_id in range(0, n, BATCH_SIZE):
            batch_from = batch_id + BATCH_SIZE_PER_RANK * RANK
            batch_to = batch_from + BATCH_SIZE_PER_RANK

            sequences = []
            # TODO: Can we implement prefetching?
            for i in range(batch_from, batch_to):
                x = train_ds[batch_id + i]
                sequences.append(
                    [
                        "Опишите следующую картинку",
                        ImageDescription(pil_image=x["image"]),
                        x["description"],
                    ]
                )

            try:
                model_input = tokenizer.encode(sequences, include_labels=True, context_size=512)
            except AssertionError:
                # TODO: This will get nodes out of sync with regard to batch id
                continue

            # TODO: Can we avoid reallocating input tensors every time?
            model_input["patches"] = model_input["patches"].to(torch.bfloat16)
            model_input = {key: value.to(device) if key != "n_ctx" else value for key, value in model_input.items()}

            labels: torch.Tensor = model_input.pop("labels")
            weights: torch.Tensor = model_input.pop("weights")

            optimizer.zero_grad()
            outputs = model(**model_input)

            logits: torch.Tensor = outputs.logits

            loss = torch.nn.functional.cross_entropy(logits.permute(0, 2, 1), labels, reduction="none")

            loss = ((loss * weights).sum(1) / weights.sum(1)).mean()
            loss.backward()

            optimizer.step()

            log("loss", loss.item(), batch_id)
            pbar.update(BATCH_SIZE)

            # if batch_id > next_stat:
            #     print_stats(model.module, batch_id)
            #     next_stat = batch_id + STATS_EVERY

            if batch_id > next_checkpoint:
                checkpoint(model.module, batch_id)
                next_checkpoint = min(next_checkpoint * CHECKPOINT_INC, next_checkpoint + CHECKPOINT_TOP)


if __name__ == "__main__":
    dist.init_process_group("nccl")
    main()
