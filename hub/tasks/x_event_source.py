import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hub.api.v1.registry import agents_with_x_accounts_to_track
from hub.tasks.near_events import run_agent
from hub.tasks.twitter_client import get_latest_mentions

logger = logging.getLogger(__name__)

RESET_TWEET_TIMESTAMP_ON_START = True  # reusing setting name for now

# Path to store the last read tweet id
TWEET_STATUS_FILE = "last_tweet.txt"

scheduler = AsyncIOScheduler()


def get_user_last_tweet_filename(user_name=""):
    return TWEET_STATUS_FILE.replace(".txt", f"_{user_name}.txt")


X_ACCOUNTS_TO_TRACK = {}

registry_items_with_x_accounts_to_track = agents_with_x_accounts_to_track()
for registry_item in registry_items_with_x_accounts_to_track:
    x_accounts_to_add = registry_item.details.get("agent", {}).get("x_accounts_to_track", [])
    if isinstance(x_accounts_to_add, list):
        for x_account_to_add in x_accounts_to_add:
            # check if this agent already tracking this x account
            agent_already_track_this_x_account = False
            for agent_entry_data in X_ACCOUNTS_TO_TRACK.get(x_account_to_add, []):
                if (
                    agent_entry_data.namespace == registry_item.namespace
                    and agent_entry_data.name == registry_item.name
                ):
                    agent_already_track_this_x_account = True
                    break

            if not agent_already_track_this_x_account:
                if x_account_to_add in X_ACCOUNTS_TO_TRACK.keys():
                    X_ACCOUNTS_TO_TRACK[x_account_to_add].append(registry_item)
                else:
                    X_ACCOUNTS_TO_TRACK[x_account_to_add] = [registry_item]


# remove last known tweet timestamp to reset the state on start
if RESET_TWEET_TIMESTAMP_ON_START:
    for x_account_to_add in X_ACCOUNTS_TO_TRACK:
        filename = get_user_last_tweet_filename(x_account_to_add)
        if os.path.exists(filename):
            os.remove(filename)
            print(f"File {filename} has been deleted.")


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


async def listener_function(auth_token, tweet, agents_entries):
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
                # Replace URLs in text
                if "://t.co/" in url_data["url"]:
                    message["text"] = tweet.text.replace(url_data["url"], url_data["display_url"])
                else:
                    message["text"] = tweet.text.replace(url_data["url"], url_data["expanded_url"])

    for agent_entry in agents_entries:
        agent = f"{agent_entry.namespace}/{agent_entry.name}/{agent_entry.version}"
        logger.info(f"Scheduling agent {agent} run for message {tweet.text}")
        await run_agent(
            agent,
            message,
            auth_token,
        )


# Main asynchronous function to process fetch and process tweets
async def x_events_task(auth_token):
    # Get the last processed tweet timestamp

    x_tasks = []
    for user_name in X_ACCOUNTS_TO_TRACK.keys():
        last_tweet_timestamp = await get_last_tweet_timestamp(user_name)

        # load latest mentions
        tweets = await get_latest_mentions(user_name, last_tweet_timestamp)

        if tweets:
            for tweet in reversed(tweets):
                tweet_timestamp = int(tweet.created_at.timestamp())
                #  Check if the tweet is newer than the last processed tweet
                if not last_tweet_timestamp or tweet_timestamp > int(last_tweet_timestamp):
                    # Ensure the tweet is not already in x_tasks by checking its ID
                    if not any(existing_task.get("tweet").id == tweet.id for existing_task in x_tasks):
                        x_tasks.append({"tweet": tweet, "agents": X_ACCOUNTS_TO_TRACK[user_name]})

                    last_tweet_timestamp = tweet_timestamp

                    # local_mode supports only single task
                    # return True
                else:
                    print(f"Tweet is too old: {tweet_timestamp} < {last_tweet_timestamp}")

        if last_tweet_timestamp:
            save_last_tweet_time(last_tweet_timestamp, user_name)

    for task in x_tasks:
        tweet = task.get("tweet")
        await listener_function(auth_token, tweet, task.get("agents"))
