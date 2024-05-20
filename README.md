# Jasnah CLI

## Setup

First install jasnah-cli by running:

```
git clone jasnah-cli
cd jasnah-cli
python3 -m pip install -e .
pip install openai
```

Check the installation worked with

```
jasnah-cli version
```

Setup basic configuration

```
jasnah-cli config set db_user <DB_USERNAME>
jasnah-cli config set db_password <DB_PASSWORD>
jasnah-cli config set user_name <YOUR_NAME>
```

The user name will be used to identify the author of the experiments.
This configuration can be manually edited at `~/.jasnah/config.json`, or per project at `.jasnah/config.json` (relative to the current directory).

To use the registry (for downloading and uploading models and datasets) you need to setup access to S3. Do it by installing [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) and configuring it:

```
export AWS_ACCESS_KEY_ID=<..>
export AWS_SECRET_ACCESS_KEY="<..>"
```

## Usage

### Submit an experiment

To submit a new experiment run:

```
jasnah-cli submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as jasnah-cli are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `jasnah.CONFIG.supervisor_id`. See [examples/prepare_data.py](examples/prepare_data.py) for an example.


### Registry

Upload a new dataset or model to the reigstry:

```
jasnah-cli model upload --path <PATH_TO_MODEL> --name <MODEL_NAME>
jasnah-cli dataset upload --path <PATH_TO_DATASET> --name <MODEL_NAME>
```

The path could be either to a file or a folder.


### Library

You can import `jasnah` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
- Store log events in the database. TODO Example.
- Fetch information about running or past experiments. TODO Example.
