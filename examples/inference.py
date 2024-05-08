from transformers.pipelines.conversational import Conversation

from jasnah.dataset import load_dataset
from jasnah.inference import InferenceSession
from jasnah.model import get_model


def main():
    ds = load_dataset("test/school_math/v1")
    model_path = get_model("base/llama-3-8b-instruct")

    session = InferenceSession(model_path, stop_token=128009)

    for row in ds:
        if (
            row["answer_kind"] != "Precise"
            or not isinstance(row["answer"], str)
            or len(row["answer"]) == 0
        ):
            continue

        conversation = Conversation()

        conversation.add_message(
            {
                "role": "system",
                "content": "You are a helpful assistant capable of solving math problems. The problem statement will be given in Russian, and it could include Latex in it. You should provide a step-by-step solution within <solution> tags, then you should provide the final answer within <answer> tags. Don't provide any extra information.",
            }
        )

        conversation.add_message(
            {
                "role": "user",
                "content": row["problem"],
            }
        )

        result = session.generate(conversation)
        print(result)


if __name__ == "__main__":
    main()
