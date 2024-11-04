# -*- coding: utf-8 -*-
import json
import os
import shutil
import time
from subprocess import call
from typing import Optional

import boto3
from aws_runner.partial_near_client import PartialNearClient
from nearai.agents.agent import Agent
from nearai.agents.environment import Environment
from shared.auth_data import AuthData
from shared.client_config import ClientConfig
from shared.inference_client import InferenceClient
from shared.near.sign import SignatureVerificationResult, verify_signed_message
from shared.provider_models import PROVIDER_MODEL_SEP

cloudwatch = boto3.client("cloudwatch", region_name="us-east-2")

PATH = "/tmp/agent-runner-docker/environment-runs"
RUN_PATH = PATH + "/run"
DEFAULT_API_URL = "https://api.near.ai"


def handler(event, context):
    start_time = time.perf_counter()
    required_params = ["agents", "auth"]
    agents = event.get("agents")
    auth = event.get("auth")
    if not agents or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = auth if isinstance(auth, AuthData) else AuthData(**auth)
    start_time_val = time.perf_counter()
    verification_result = verify_signed_message(
        auth_object.account_id,
        auth_object.public_key,
        auth_object.signature,
        auth_object.message,
        auth_object.nonce,
        auth_object.recipient,
        auth_object.callback_url,
    )

    if verification_result == SignatureVerificationResult.VERIFY_ACCESS_KEY_OWNER_SERVICE_NOT_AVAILABLE:
        write_metric("AdminNotifications", "SignatureAccessKeyVerificationServiceFailed", "Count")
    elif not verification_result:
        return "Unauthorized: Invalid signature"
    else:
        # signature is valid
        stop_time_val = time.perf_counter()
        write_metric("VerifySignatureDuration", stop_time_val - start_time_val)

    environment_id = event.get("environment_id")
    new_message = event.get("new_message")
    thread_id = event.get("thread_id")
    run_id = event.get("run_id")

    params = event.get("params", {})

    new_environment_registry_id = run_with_environment(
        agents,
        auth_object,
        thread_id,
        run_id,
        new_message=new_message,
        params=params,
    )
    if not new_environment_registry_id:
        return f"Run not recorded. Ran {agents} agent(s) with generated near client and environment {environment_id}"

    call("rm -rf /tmp/..?* /tmp/.[!.]* /tmp/*", shell=True)
    stop_time = time.perf_counter()
    write_metric("TotalRunnerDuration", stop_time - start_time)
    return new_environment_registry_id


def write_metric(metric_name, value, unit="Milliseconds", verbose=True):
    if os.environ.get("AWS_ACCESS_KEY_ID"):  # running in lambda or locally passed credentials
        cloudwatch.put_metric_data(
            Namespace="NearAI",
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": [
                        {"Name": "FunctionName", "Value": os.environ["AWS_LAMBDA_FUNCTION_NAME"]},
                    ],
                }
            ],
        )
    elif verbose:
        print(f"Would have written metric {metric_name} with value {value} to cloudwatch")


def load_agent(
    client, agent, params: dict, account_id: str = "local", additional_path: str = "", verbose=True
) -> Agent:
    agent_metadata = None

    if params["data_source"] == "registry":
        start_time = time.perf_counter()
        agent_files = client.get_agent(agent)
        stop_time = time.perf_counter()
        write_metric("GetAgentFromRegistry_Duration", stop_time - start_time, verbose=verbose)
        agent_metadata = client.get_agent_metadata(agent)
    elif params["data_source"] == "local_files":
        agent_files = get_local_agent_files(agent, additional_path)

        for file in agent_files:
            if os.path.basename(file["filename"]) == "metadata.json":
                agent_metadata = json.loads(file["content"])
                if verbose:
                    print(f"Loaded {agent_metadata} agents from {agent}")
                break

    if not agent_metadata:
        print(f"Missing metadata for {agent}")

    return Agent(
        agent, agent_files, agent_metadata or {}, change_to_temp_dir=params.get("change_to_agent_temp_dir", True)
    )


def clear_temp_agent_files(agents, verbose=True):
    for agent in agents:
        if agent.temp_dir and os.path.exists(agent.temp_dir):
            if verbose:
                print("removed agent.temp_dir", agent.temp_dir)
            shutil.rmtree(agent.temp_dir)


def save_environment(env, client, base_id, metric_function=None) -> str:
    save_start_time = time.perf_counter()
    snapshot = env.create_snapshot()
    metadata = env.environment_run_info(base_id, "remote run")
    name = metadata["name"]
    request_start_time = time.perf_counter()
    registry_id = client.save_environment(snapshot, metadata)
    request_stop_time = time.perf_counter()
    if metric_function:
        metric_function("SaveEnvironmentToRegistry_Duration", request_stop_time - request_start_time)
    print(
        f"Saved environment {registry_id} to registry. To load use flag `--load-env={registry_id}`. "
        f"or `--load-env={name}`"
    )
    save_stop_time = time.perf_counter()
    if metric_function:
        metric_function("SaveEnvironment_Duration", save_stop_time - save_start_time)
    return registry_id


class EnvironmentRun:
    def __init__(  # noqa: D107
        self,
        near_client: PartialNearClient,
        agents: list[Agent],
        env: Environment,
        thread_id,
        record_run: bool,
        verbose: bool,
    ) -> None:
        self.near_client = near_client
        self.agents = agents
        self.env = env
        self.thread_id = thread_id
        self.record_run = record_run
        self.verbose = verbose

    def __del__(self) -> None:  # noqa: D105
        clear_temp_agent_files(self.agents, verbose=self.verbose)

    def run(self, new_message: str = "") -> Optional[str]:  # noqa: D102
        start_time = time.perf_counter()
        self.env.run(new_message, self.agents[0].max_iterations)
        stop_time = time.perf_counter()
        write_metric("ExecuteAgentDuration", stop_time - start_time, verbose=self.verbose)
        new_environment = (
            save_environment(self.env, self.near_client, self.thread_id, write_metric) if self.record_run else None
        )
        return new_environment


def start_with_environment(
    agents: str,
    auth: AuthData,
    thread_id,
    run_id,
    additional_path: str = "",
    params: Optional[dict] = None,
    print_system_log: bool = False,
) -> EnvironmentRun:
    """Initializes environment for agent runs."""
    verbose: bool = params.get("verbose", True)
    if verbose:
        print(
            f"Running with:\nagents: {agents}\nparams: {params}"
            f"\nthread_id: {thread_id}\nrun_id: {run_id}\nauth: {auth}"
        )
    params = params or {}
    api_url = str(params.get("api_url", DEFAULT_API_URL))
    user_env_vars: dict = params.get("user_env_vars", {})
    agent_env_vars: dict = params.get("agent_env_vars", {})

    if api_url != DEFAULT_API_URL and verbose:
        print(f"WARNING: Using custom API URL: {api_url}")

    near_client = PartialNearClient(api_url, auth)

    loaded_agents: list[Agent] = []
    for agent_name in agents.split(","):
        agent = load_agent(near_client, agent_name, params, auth.account_id, additional_path, verbose=verbose)
        # agents secrets has higher priority then agent metadata's env_vars
        agent.env_vars = {**agent.env_vars, **agent_env_vars.get(agent_name, {})}
        loaded_agents.append(agent)

    agent = loaded_agents[0]
    if "provider" in params:
        agent.model_provider = params["provider"]
    if "model" in params:
        model = params["model"]
        if model:
            agent.model = model
        if "provider" not in params and PROVIDER_MODEL_SEP in agent.model:
            agent.model_provider = ""
    if "temperature" in params:
        agent.model_temperature = params["temperature"]
    if "max_tokens" in params:
        agent.model_max_tokens = params["max_tokens"]
    if "max_iterations" in params:
        agent.max_iterations = params["max_iterations"]

    client_config = ClientConfig(
        base_url=api_url + "/v1",
        auth=auth,
    )
    inference_client = InferenceClient(client_config)
    hub_client = client_config.get_hub_client()
    env = Environment(
        additional_path if additional_path else RUN_PATH,
        loaded_agents,
        inference_client,
        hub_client,
        thread_id,
        run_id,
        env_vars=user_env_vars,
        print_system_log=print_system_log,
    )
    if agent.welcome_title:
        print(agent.welcome_title)
    if agent.welcome_description:
        print(agent.welcome_description)
    env.add_agent_start_system_log(agent_idx=0)
    return EnvironmentRun(near_client, loaded_agents, env, thread_id, params.get("record_run", True), verbose=verbose)


def run_with_environment(
    agents: str,
    auth: AuthData,
    thread_id,
    run_id,
    additional_path: str = "",
    new_message: str = "",
    params: Optional[dict] = None,
    print_system_log: bool = False,
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    environment_run = start_with_environment(agents, auth, thread_id, run_id, additional_path, params, print_system_log)
    return environment_run.run(new_message)


def get_local_agent_files(agent_identifier: str, additional_path: str = ""):
    """Fetches an agent from local filesystem."""
    # base_path = os.path.join("/root/.nearai/registry", agent_identifier)
    # os.path.expanduser(f"/root/.nearai/registry/{agent_identifier}")
    # base_path = os.path.expanduser(f"/nearai_registry/{agent_identifier}")
    base_path = os.path.expanduser(f"~/.nearai/registry/{agent_identifier}")

    paths = [base_path]
    if additional_path:
        paths.append(os.path.join(base_path, additional_path))

    results = []
    for path in paths:
        for root, _dirs, files in os.walk(path):
            for file in files:
                path = os.path.join(root, file)
                try:
                    with open(path, "r") as f:
                        result = f.read()
                    results.append({"filename": os.path.basename(path), "content": result})
                except Exception as e:
                    print(f"Error {path}: {e}")
    return results
