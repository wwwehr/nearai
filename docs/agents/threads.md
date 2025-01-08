# Threads

Every agent execution happens within a conversation thread, which is isolated from other threads. Threads allow agents to maintain a message history and persist files in time so the user can continue the conversation later.

---

## Starting a Thread

If we start an agent without specifying an existing thread, a new thread is created. Let's try this by executing an agent using the interactive mode:

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local

> Hello, my name is Guille, please remember it

# Example Output:
# ...
# thread_id: thread_43c64803c0a948bc9a8eb8e8

# Assistant: Nice to meet you, Guille! I've made a note of your name, so feel free to ask me anything or start a conversation, and I'll be sure to address you by your name throughout our chat. How's your day going so far, Guillermo?
```

We can see in the input that a new `thread_id` - `thread_43c64803c0a948bc9a8eb8e8` - was created for this conversation.

---

## Resuming a Thread

If we want to resume a conversation thread with an agent, we can specify the thread ID when running the agent:

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local --thread_id thread_43c64803c0a948bc9a8eb8e8

> What is my name?

# Assistant: Your name is Guille
```

---

## Persisting Data

Each thread has an storage associated, where the agent can load and save data. This allows us to persist data across different agent executions. The local file system is isolated for each thread, so you can't access files from other threads.

<hr class="subsection">

### Storing Data

To create a new file in the thread we can use the `write_file` method from the environment:

```python title="agent.py"
def run(env: Environment):
  env.write_file('file.txt', 'hello thread')
```

??? tip "Where is the file stored?"

    When running the agent locally, a temporary folder will be created to store each thread data. We can check exactly where the file is stored by using the `python debugger`:

    ```python title="agent.py"
    def run(env: Environment):
      env.write_file('file.txt', 'hello thread')
      import ipdb; ipdb.set_trace()  # Call the ipdb debugger
    ```

    After running the agent, we will be dropped into the debugger, where we can check the current working directory:

    ```bash
    nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local --thread_id thread_43c64803c0a948bc9a8eb8e8

    ipdb> import os; os.getcwd() # Check the current working directory
    '/private/var/folders/v6/pw4e3e3r5t6h8i9oihtd9d7d1234df/T/agent_7e312s678b987sa4vc4s2zxs2s1w1345'
    ```

    We can see that the current working directory is a temporary folder. Go ahead and start the `agent` again without the `--thread_id` parameter, you will see that the working directory changes.

<hr class="subsection">

### Accesing Files

To list the files in the thread storage, we can use the `list_files_from_thread` method from the environment:

```python title="agent.py"
def run(env: Environment):
  files = env.list_files_from_thread()
  content = env.read_file('file.txt')

  print('Files:', files)
  print('Content of file.txt:', content)
```

??? example "Example Output"
    ```python
    Files [FileObject(id='file_31aab645e3214a13b402e321', bytes=12, created_at=1734733634, filename='file.txt', object='file', purpose='assistants', status='uploaded', status_details='File information retrieved successfully')]

    Content of file.txt hello thread
    ```
