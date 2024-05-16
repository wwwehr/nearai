# Jasnah CLI

## Installation

```
git clone jasnah-cli
cd jasnah-cli
python3 -m pip install -e .
```

To install to a virtual environment, use the following command:

```bash
python3 -m poetry install --no-root --with dev
```

## Usage

```
jasnah-cli --help
```

## TODO

-   Create alias for models and datasets on the database. For example

`llama-3-8b-instruct` could point to `base/llama-3-8b-instruct-fp32`
`best-math-model` could point to the best fine-tuned model we have so far (this changes over time).
