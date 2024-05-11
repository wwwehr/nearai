from dataclasses import asdict
from random import choice
from typing import Optional

import requests
from flask import Flask, request

import jasnah
from jasnah.config import CONFIG
from jasnah.supervisor import TaskDescription

app = Flask(__name__)
CONFIG.origin = "server"


@app.route("/status")
def status():
    return "Server Ok!\n"


@app.post("/submit")
def submit():
    task = TaskDescription(**request.json)

    supervisor = choice(CONFIG.supervisors)

    jasnah.log({"supervisor": supervisor, "task": asdict(task)})

    result = requests.post(supervisor + "/submit", json=request.json)

    print(result, result.text)
    return "Submission Ok!\n"


def run_server():
    app.run("0.0.0.0", 8100)


class ServerClient:
    def __init__(self, url):
        self.url = url
        self.conn = requests.Session()

    def status(self):
        result = self.conn.get(self.url + "/status")
        return result.text

    def submit(
        self, repository: str, commit: str, command: str, diff: Optional[str] = None
    ):
        result = self.conn.post(
            self.url + "/submit",
            json=dict(repository=repository, commit=commit, command=command, diff=diff),
        )
        print(result, result.text)


if __name__ == "__main__":
    client = ServerClient("http://127.0.0.1:8100")
    print(client.status())
    client.submit(
        "git@github.com:nearai/jasnah-cli.git",
        "d215f25fdd3e56ccb802e72a9481ffc240c13643",
        "python3 examples/simple_task.py",
    )
