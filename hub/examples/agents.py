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
thread = client.beta.threads.create()
logger.info(f"Thread created with ID: {thread.id}")

# Add a message to the thread
logger.info("Adding a message to the thread")
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Hello! Can you help me with planning my trip to Lisbon?"
)

messages = client.beta.threads.messages.list(thread.id)
logger.info(f"Messages in thread: {messages}")


# Execute a run on the assistant
logger.info("Executing a run on the assistant")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="badisland7754.near/inter-agents/0.0.1",
    instructions="Please provide a helpful response.",
    model="fireworks::llama-v3p1-70b-instruct"
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
logger.info(f"Messages in thread: {messages}")

logger.info("Agent execution process completed")

