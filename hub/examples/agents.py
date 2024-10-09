import openai
import json
import os
import nearai
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

hub_url = "http://localhost:8000/v1"

logger.info("Starting the agent execution process")

# Login to NEAR AI Hub using nearai CLI.
# Read the auth object from ~/.nearai/config.json
auth = nearai.config.load_config_file()["auth"]
signature = json.dumps(auth)

logger.info("Authenticated with NEAR AI Hub")

client = openai.OpenAI(base_url=hub_url, api_key=signature)

# Create a new thread
logger.info("Creating a new thread")
thread = client.beta.threads.create(
    tool_resources=
)
logger.info(f"Thread created with ID: {thread.id}")

# Add a message to the thread
logger.info("Adding a message to the thread")
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Hello! Can you help me with planning my trip to Lisbon?"
)

logger.info(f"Message added to thread: {message.id}")
logger.info(f"Message content: {message.content}")

# Execute a run on the assistant
logger.info("Executing a run on the assistant")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="flatirons.near/example-travel-agent/1",
    model="fireworks::llama-v3p1-70b-instruct",
)

logger.info(f"Run created with ID: {run.id}")
logger.info(f"Initial run status: {run.status}")

# Wait for the run to complete
logger.info("Waiting for the run to complete")
while run.status != "completed":
    time.sleep(5)
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    logger.info(f"Current run status: {run.status}")

logger.info("Run completed")

# Retrieve the assistant's response
logger.info("Retrieving the assistant's response")
messages = client.beta.threads.messages.list(thread_id=thread.id)
assistant_message = next((msg for msg in messages.data if msg.role == "assistant"), None)

if assistant_message:
    logger.info("Assistant's response received")
    print("Assistant's response:")
    print(assistant_message.content[0].text.value)
else:
    logger.warning("No response received from the assistant")
    print("No response from the assistant.")

logger.info("Agent execution process completed")

