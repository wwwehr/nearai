"""
Converts processed school math dataset, into json format for training.
"""

import json
from pathlib import Path

from jasnah.dataset import get_dataset, load_dataset

INPUT = """
<problem>
{problem}
</problem>
"""

OUTPUT = """
<solution>
{solution}
</solution>

<answer>
{answer}
</answer>
"""


def main():
    dataset = load_dataset("school_math_ru")
    dataset_path = get_dataset("school_math_ru")
    
    # Prepare a list to store formatted data
    formatted_data = []
    
    # Iterate through each record in the dataset
    for example in dataset:
        input_text = INPUT.format(problem=example['problem'])
        output_text = OUTPUT.format(solution=example['solution'], answer=example['answer'])
        # Create a JSON-like dictionary and add it to the list
        formatted_data.append(json.dumps({"input": input_text, "output": output_text}))
    
    # Write the formatted data to a JSON file
    json_path = dataset_path / "training_data.json"
    with open(json_path, 'w') as f:
        f.write("\n".join(formatted_data))
    
    print(f"Data saved to {json_path}")

if __name__ == "__main__":
    main()
