"""
Converts processed school math dataset, into json format for training.
"""

import json
from pathlib import Path

from jasnah.model import get_model

def main():
    get_model("llama-3-8b")

if __name__ == "__main__":
    main()
