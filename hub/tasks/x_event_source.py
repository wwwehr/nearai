import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hub.tasks.near_events import run_agent
from hub.tasks.twitter_client import get_latest_mentions

logger = logging.getLogger(__name__)

RESET_TWEET_TIMESTAMP_ON_START = True  # reusing setting name for now

# Path to store the last read tweet id
TWEET_STATUS_FILE = "last_tweet.txt"

scheduler = AsyncIOScheduler()

# future: pull from registry 'integration' item
ACCOUNTS_TO_TRACK = ["nearai_intern", "zacodil"]

# future: pull from agent metadata
LISTENER_CONFIG = {"agent_name": "agent.raidvault.near/airdrop/0.11"}


def get_user_last_tweet_filename(user_name=""):
    return TWEET_STATUS_FILE.replace(".txt", f"_{user_name}.txt")


# Function to get the last read tweet timestamp from a file
async def get_last_tweet_timestamp(user_name=""):
    filename = get_user_last_tweet_filename(user_name)
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return int(f.read().strip())
    return None


def save_last_tweet_time(tweet_timestamp, user_name=""):
    filename = get_user_last_tweet_filename(user_name)
    with open(filename, "w") as f:
        f.write(str(int(tweet_timestamp)))


async def listener_function(auth_token, tweet):
    message = {
        "action": "twitter_mention",
        "author_id": tweet.author_id,
        "tweet_id": tweet.id,
        "tweet": tweet.data,
        "text": tweet.text,
        "replied_to": [],
    }

    # add replied_to
    if "referenced_tweets" in tweet.data:
        for referenced_tweet in tweet.data["referenced_tweets"]:
            if referenced_tweet["type"] == "replied_to":
                message["replied_to"].append(referenced_tweet["id"])

    # convert urls (t.co/ => url text)
    if "entities" in tweet.data:
        if "urls" in tweet.data["entities"]:
            for url_data in tweet.data["entities"]["urls"]:
                if "://t.co/" in url_data["url"]:
                    tweet.text = tweet.text.replace(url_data["url"], url_data["display_url"])
                else:
                    tweet.text = tweet.text.replace(url_data["url"], url_data["expanded_url"])

    await run_agent(
        LISTENER_CONFIG["agent_name"],
        message,
        auth_token,
    )


# Main asynchronous function to process fetch and process tweets
async def x_events_task(auth_token):
    # Get the last processed tweet timestamp

    x_tasks = []
    for user_name in ACCOUNTS_TO_TRACK:
        last_tweet_timestamp = await get_last_tweet_timestamp(user_name)

        # load latest mentions
        tweets = await get_latest_mentions(user_name, last_tweet_timestamp)

        if tweets:
            for tweet in reversed(tweets):
                tweet_timestamp = int(tweet.created_at.timestamp())
                #  Check if the tweet is newer than the last processed tweet
                if not last_tweet_timestamp or tweet_timestamp > int(last_tweet_timestamp):
                    # Ensure the tweet is not already in x_tasks by checking its ID
                    if not any(existing_tweet.id == tweet.id for existing_tweet in x_tasks):
                        x_tasks.append(tweet)

                    last_tweet_timestamp = tweet_timestamp

                    # local_mode supports only single task
                    # return True
                else:
                    print(f"Tweet is too old: {tweet_timestamp} < {last_tweet_timestamp}")

        save_last_tweet_time(last_tweet_timestamp, user_name)

    for tweet in x_tasks:
        logger.info("Scheduling new agent run for message", tweet.text)
        await listener_function(auth_token, tweet)


def process_x_events_initial_state():
    # remove last known tweet timestamp to reset the state on start
    if RESET_TWEET_TIMESTAMP_ON_START:
        if os.path.exists(TWEET_STATUS_FILE):
            os.remove(TWEET_STATUS_FILE)
            print(f"File {TWEET_STATUS_FILE} has been deleted.")
