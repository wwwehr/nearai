from typing import Any, Dict, Optional

import requests
from flask import Flask, request

from jasnah.config import CONFIG
from jasnah.db import db
from jasnah.supervisor import SupervisorClient

app = Flask(__name__)
CONFIG.origin = "server"


def update_queue():
    """Check for pending experiments and available supervisors"""
    result = db.get_work_unit()

    if result is None:
        return {"info": "No pending experiments or available supervisors"}

    experiment, supervisor = result

    client = SupervisorClient(supervisor.endpoint)
    result = client.update()

    return {
        "experiment": experiment,
        "supervisor": supervisor,
        "supervisor_result": result,
    }


@app.route("/status")
def status():
    experiments = db.pending_experiments(4)
    return {"status": "ok", "pending_experiments": experiments}


@app.route("/update")
def update():
    return update_queue()


@app.post("/submit")
def submit():
    body: Dict[str, Any] = request.json

    # TODO: Allow selecting multiple nodes

    name = body["name"]
    author = body["author"]
    repository = body["repository"]
    commit = body["commit"]
    command = body["command"]
    diff = body.get("diff")

    experiment_id = db.new_experiment(name, author, repository, commit, command, diff)

    result = {"status": "ok", "experiment": experiment_id}

    update_queue()

    experiment = db.get_experiment(experiment_id)

    if experiment is not None:
        result.update(
            {
                "name": experiment.name,
                "status": experiment.status,
                "assigned": experiment.assigned,
            }
        )

    return result


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
        self,
        name: str,
        repository: str,
        commit: str,
        command: str,
        diff: Optional[str] = None,
        author: Optional[str] = None,
    ):
        if author is None:
            author = CONFIG.user_name

        result = self.conn.post(
            self.url + "/submit",
            json=dict(
                name=name,
                author=author,
                repository=repository,
                commit=commit,
                command=command,
                diff=diff,
            ),
        )
        return result.json()


if __name__ == "__main__":
    client = ServerClient("http://127.0.0.1:8100")
    print(client.status())
    print(
        client.submit(
            "test_experiment",
            "git@github.com:nearai/jasnah-cli.git",
            "d215f25fdd3e56ccb802e72a9481ffc240c13643",
            "python3 examples/simple_task.py",
        )
    )
