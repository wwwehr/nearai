# The Registry: Finding and Running Agents

NearAI agents can be stored in a common registry, allowing users to share their agents with others. Let's take a look at how we can navigate the registry, download agents, and contribute our own agents to the ecosystem.

---

## Finding an Agent

There are two main ways to navigate the registry to find agents: through the [Web AI Hub](https://app.near.ai/agents), or using the [NearAI CLI](./agents/quickstart.md):


```bash
# List all agents
nearai registry list --category agent
```

??? experiment "Example Output"

    ```shell
    ┌─────────────────────────────────┬─────────────────────────┬───────┐
    │ entry                           │ description             │ tags  │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ zavodil.near/ai16z-docs/1.03    │ AI agent with AI16Z ... │ agent │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ flatirons.near/common-tool...   │ A library of common ..  │ llama │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ jayzalowitz.near/example_a...   │ Example agent           │       │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ ...                             │ ...                     │ ...   │
    └─────────────────────────────────┴─────────────────────────┴───────┘
    ```

!!! tip
    You can run the agents **directly on the [Web AI Hub](https://app.near.ai/agents)** to see how they work

---

## Downloading an Agent

Once you find an agent that you would like to download, you can use the `download` command to pull it down to your local machine. The command expects an agent of the form:

```bash
nearai registry download <account.near>/<agent_name>/<version>
```

Where version can be a specific version number, or `latest` to download the most recent version, for example: 

```bash 
# Download a hello world agent
nearai registry download gagdiez.near/hello-ai/latest
```

By default, the agent will be **downloaded to the `~/.nearai/registry` local directory**, for example the agent above will be downloaded to `~/.nearai/registry/gagdiez.near/hello-ai/latest`.

!!! tip
    The `--force` flag allows you to overwrite the local agent with the version from the registry.

---

## Running the Agent Locally

After downloading an agent you can execute it in two different ways: interactively or as a task.

Know that you can also run agents **directly on the [Web AI Hub](https://app.near.ai/agents)**, you don't need to download an agent if you just want to see how they work.

!!! danger "Always Review the Code"
    Agents can execute arbitrary code on your machine, so please always review the agent's code before running it!
    
    By default, you will find the agent's code on the local directory `~/.nearai/registry`, there, check the agent's `agent.py` file either by using the `cat` command or opening it in a text editor.

    ```bash
    # Checking gagdiez.near/hello-ai/latest code
    cd ~/.nearai/registry/gagdiez.near/hello-ai/latest
    cat agent.py
    ```

<hr class="subsection">

### Interactive Run

Interactive runs execute the agent on a loop, allowing you to chat with it interactively until you decide to exit (using the `exit` command), or quit the session using `ctrl+c`.

```bash
# Running the agent by absolute path
nearai agent interactive ~/.nearai/registry/gagdiez.near/hello-ai/latest --local
```

<hr class="subsection">

### Running as a Task
When running an agent as a task, we simply provide an input and let the agent execute it without any user interaction.

```bash
nearai agent task ~/.nearai/registry/gagdiez.near/hello-ai/latest "write a poem about the sorrow of loosing oneself, but end on a positive note" --local
```

## Running the Agent Remotely

Agents can be run through the `/thread/runs`, `/thread/{thread_id}/runs` or  `/agent/runs` endpoints. The /thread syntax
matches the OpenAI / LangGraph API. The /agent syntax is NearAI specific.

You will need to pass a signed message to authenticate. This example uses the credentials written by `nearai login` to
your `~/.nearai/config.json` file.

```shell
auth_json=$(jq -c '.auth' ~/.nearai/config.json);

curl "https://api.near.ai/v1/threads/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header "Authorization: Bearer $auth_json" \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5.0.1",
    "new_message":"Build a backgammon game",
    "max_iterations": "1"
  }
EOF
```

The full message will look like this. A `thread_id` param can also be passed to continue a previous conversation. 
```shell
curl "https://api.near.ai/v1/threads/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header 'Authorization: Bearer {"account_id":"your_account.near","public_key":"ed25519:YOUR_PUBLIC_KEY","signature":"A_REAL_SIGNATURE","callback_url":"https://app.near.ai/","message":"Welcome to NEAR AI Hub!","recipient":"ai.near","nonce":"A_UNIQUE_NONCE_FOR_THIS_SIGNATURE"}' \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5.0.1",
    "thread_id": "a_previous_thread_id",
    "new_message":"Build a backgammon game", 
    "max_iterations": "2"
  }
EOF
```

??? tip "Remote results"
    The results of the /agent/runs endpoints are either an error or the resulting thread_id.
    >"thread_579e1cf3f42742c785218106"

    Threads follow the OpenAI / LangGraph api standard. `/threads/{thread_id}/messages` will return the messages on the thread.
    See the full NearAI OpenAPI spec here: [https://api.near.ai/openapi.json](https://api.near.ai/openapi.json)

---

## Uploading an Agent

If you created an agent and would like to share it with others, you can upload it to the registry. To upload an agent, you must have a [**logged in**](./agents/quickstart.md#login-to-nearai).

The `upload` command expects the path to the agent's local directory, for example:

```bash
nearai registry upload ~/.nearai/registry/<your-account.near>/<agent_folder>
```

The folder must contain an `agent.py` file, where the agent's logic is written, and a `metadata.json` file that holds information such as a description, tags, and the model used by the agent.

!!! tip "Tags"
    Remember to add tags to your agent to make it easier for others to find it in the registry, for example:
    
    ```json
    { "tags": ["travel", "assistant", "vacation"] }
    ```

!!! danger
    **All files** in this folder **will be uploaded** to the registry! Make sure you are not including any sensitive data

!!! warning
    You can't remove or overwrite a file once it's uploaded, but you can hide the entire agent by setting the `"show_entry": false` field in the `metadata.json` file