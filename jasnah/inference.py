import time
from typing import Optional, Union

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.pipelines.conversational import Conversation


class InferenceSession:
    def __init__(
        self,
        model_name: str,
        *,
        stop_string: Optional[str] = None,
        stop_token: Optional[int] = None,
        peft_model: Optional[str] = None,
    ):
        torch.cuda.manual_seed(42)
        torch.manual_seed(42)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        self.stop_string = stop_string
        self.stop_token = stop_token

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            return_dict=True,
            load_in_8bit=False,
            device_map="auto",
            low_cpu_mem_usage=True,
            attn_implementation="sdpa",
        )

        if peft_model is not None:
            self.model = PeftModel.from_pretrained(self.model, peft_model)

        self.model.eval()

    def generate(self, prompt: Union[str, Conversation]):
        if isinstance(prompt, str):
            batch = self.tokenizer(prompt, return_tensors="pt")
        else:
            batch = self.tokenizer.apply_chat_template(
                prompt, return_tensors="pt", return_dict=True
            )

        batch = {k: v.to("cuda") for k, v in batch.items()}

        start = time.perf_counter()
        with torch.no_grad():
            outputs = self.model.generate(
                **batch,
                max_new_tokens=1024,
                do_sample=True,
                top_p=1.0,
                temperature=0.1,
                use_cache=True,
                eos_token_id=self.stop_token,
                pad_token_id=self.tokenizer.eos_token_id,
                stop_strings=self.stop_string,
            )

        e2e_inference_time = (time.perf_counter() - start) * 1000
        print(f"the inference time is {e2e_inference_time} ms")

        output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        return output_text

    def chat(self, conversation: Conversation, generate_config: dict = {}):
        input = self.tokenizer.apply_chat_template(
            conversation, return_tensors="pt", return_dict=True
        )

        input = {k: v.to("cuda") for k, v in input.items()}

        input_len = input["input_ids"].shape[-1]

        start = time.perf_counter()
        with torch.no_grad():
            outputs = self.model.generate(
                **input,
                **generate_config,
                eos_token_id=self.stop_token,
                pad_token_id=self.tokenizer.eos_token_id,
                stop_strings=self.stop_string,
            )
        e2e_inference_time_ms = (time.perf_counter() - start) * 1000
        answer = self.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
        output_len = outputs[0].shape[-1] - input_len

        return {
            "time_ms": e2e_inference_time_ms,
            "answer": answer,
            "input_tokens": input_len,
            "output_tokens": output_len,
        }
