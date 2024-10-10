# -*- coding: utf-8 -*-
import json
import os
import shutil
import time
from subprocess import call
from typing import Optional

import boto3
import openai
from aws_runner.partial_near_client import PartialNearClient
from nearai.agents.agent import Agent
from nearai.agents.environment import Environment
from shared.client_config import ClientConfig
from shared.inference_client import InferenceClient
from shared.near.sign import SignatureVerificationResult, verify_signed_message

cloudwatch = boto3.client("cloudwatch", region_name="us-east-2")

PATH = "/tmp/agent-runner-docker/environment-runs"
RUN_PATH = PATH + "/run"
FUNCTION_NAME = os.environ["AWS_LAMBDA_FUNCTION_NAME"]
DEFAULT_API_URL = "https://api.near.ai"


def handler(event, context):
    start_time = time.perf_counter()
    required_params = ["agents", "auth"]
    agents = event.get("agents")
    auth = event.get("auth")
    if not agents or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = auth if isinstance(auth, dict) else json.loads(auth)

    start_time_val = time.perf_counter()
    verification_result = verify_signed_message(
        auth_object.get("account_id"),
        auth_object.get("public_key"),
        auth_object.get("signature"),
        auth_object.get("message"),
        auth_object.get("nonce"),
        auth_object.get("recipient"),
        auth_object.get("callback_url"),
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
    thread_id = event.get("environment_id")  # TODO: migrate to thread_id
    model = event.get("model")

    params = event.get("params", {})

    new_environment_registry_id = run_with_environment(
        agents,
        auth_object,
        environment_id,
        new_message,
        params,
        thread_id,
        model,
    )
    if not new_environment_registry_id:
        return f"Run not recorded. Ran {agents} agent(s) with generated near client and environment {environment_id}"

    call("rm -rf /tmp/..?* /tmp/.[!.]* /tmp/*", shell=True)
    stop_time = time.perf_counter()
    write_metric("TotalRunnerDuration", stop_time - start_time)
    return new_environment_registry_id


def write_metric(metric_name, value, unit="Milliseconds"):
    if os.environ.get("AWS_ACCESS_KEY_ID"):  # running in lambda or locally passed credentials
        cloudwatch.put_metric_data(
            Namespace="NearAI",
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": [
                        {"Name": "FunctionName", "Value": FUNCTION_NAME},
                    ],
                }
            ],
        )
    else:
        print(f"Would have written metric {metric_name} with value {value} to cloudwatch")


def load_agent(client, agent, params: dict = None):
    agent_metadata = None
    print("agent", agent, "params", params)
    if params["data_source"] == "registry":
        start_time = time.perf_counter()
        agent_files = client.get_agent(agent)
        stop_time = time.perf_counter()
        write_metric("GetAgentFromRegistry_Duration", stop_time - start_time)
        agent_metadata = client.get_agent_metadata(agent)
    elif params["data_source"] == "local_files":
        agent_files = get_local_agent_files(agent)

        for file in agent_files:
            if os.path.basename(file["filename"]) == "metadata.json":
                agent_metadata = json.loads(file["content"])
                print(f"Loaded {agent_metadata} agents from {agent}")
                break

    if not agent_metadata:
        print(f"Missing metadata for {agent}")

    return Agent(agent, agent_files, agent_metadata or {})


def clear_temp_agent_files(agents):
    for agent in agents:
        if agent.temp_dir and os.path.exists(agent.temp_dir):
            print("removed agent.temp_dir", agent.temp_dir)
            shutil.rmtree(agent.temp_dir)


def save_environment(env, client, run_id, base_id, metric_function=None) -> str:
    save_start_time = time.perf_counter()
    snapshot = env.create_snapshot()
    metadata = env.environment_run_info(run_id, base_id, "remote run")
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


def run_with_environment(
    agents: str,
    auth: dict,
    thread_id,
    model,
    environment_id: str = None,
    new_message: str = None,
    params: dict = None,
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    print("Running with :", agents, auth, environment_id, new_message, params, thread_id)
    params = params or {}
    max_iterations = int(params.get("max_iterations", 2))
    record_run = bool(params.get("record_run", True))
    api_url = str(params.get("api_url", DEFAULT_API_URL))
    user_env_vars: dict = params.get("user_env_vars", {})
    agent_env_vars: dict = params.get("agent_env_vars", {})

    if api_url != DEFAULT_API_URL:
        print(f"WARNING: Using custom API URL: {api_url}")

    near_client = PartialNearClient(api_url, auth)
    hub_client = openai.OpenAI(base_url=api_url + "/v1", api_key=f"Bearer {json.dumps(auth)}")

    loaded_agents = []

    for agent_name in agents.split(","):
        agent = load_agent(near_client, agent_name, params)
        # agents secrets has higher priority then agent metadata's env_vars
        agent.env_vars = {**agent.env_vars, **agent_env_vars.get(agent_name, {})}
        loaded_agents.append(agent)

    client_config = ClientConfig(
        base_url=api_url + "/v1",
        auth=auth,
    )
    inference_client = InferenceClient(client_config)

    env = Environment(
        RUN_PATH,
        loaded_agents,
        inference_client,
        hub_client,
        thread_id,
        model,
        env_vars=user_env_vars,
    )
    start_time = time.perf_counter()
    env.add_agent_start_system_log(agent_idx=0)
    run_id = env.run(new_message, max_iterations)
    new_environment = save_environment(env, near_client, run_id, environment_id, write_metric) if record_run else None
    clear_temp_agent_files(loaded_agents)
    stop_time = time.perf_counter()
    write_metric("ExecuteAgentDuration", stop_time - start_time)
    return new_environment


def get_local_agent_files(agent_identifier: str):
    """Fetches an agent from local filesystem."""
    # base_path = os.path.join("/root/.nearai/registry", agent_identifier)
    # os.path.expanduser(f"/root/.nearai/registry/{agent_identifier}")
    # base_path = os.path.expanduser(f"/nearai_registry/{agent_identifier}")
    base_path = os.path.expanduser(f"~/.nearai/registry/{agent_identifier}")
    print("base_path", base_path)

    results = []

    for root, _dirs, files in os.walk(base_path):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, "r") as f:
                    result = f.read()
                results.append({"filename": os.path.basename(path), "content": result})
            except Exception as e:
                print(f"Error {path}: {e}")

    print("results", results)

    return results
