from jasnah.dataset import load_dataset
from jasnah.inference import InferenceSession
from jasnah.model import get_model


def main():
    model_path = get_model("base/llama-3-8b-instruct")
    session = InferenceSession(model_path)

    # ds = load_dataset("test/school_math/v1")

    result = session.generate("What is 2+2?")
    print(result)


if __name__ == "__main__":
    main()
