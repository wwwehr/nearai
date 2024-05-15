from dataclasses import asdict
from typing import Any, Dict, Optional

import requests
from flask import Flask, request

import jasnah
from jasnah.config import CONFIG
from jasnah.db import db
from jasnah.supervisor import SupervisorClient

app = Flask(__name__)


@app.route("/status")
def status():
    experiments = db.last_experiments(2)
    return {
        "status": "ok",
        "last_experiments": experiments,
        "supervisors": CONFIG.supervisors,
    }


@app.post("/submit")
def submit():
    # TODO: Move to create_app method
    CONFIG.origin = "server"

    body: Dict[str, Any] = request.json

    name = body["name"]
    author = body["author"]
    repository = body["repository"]
    commit = body["commit"]
    diff = body.get("diff")
    command = body["command"]
    num_nodes = body["num_nodes"]
    cluster = body["cluster"]

    experiment_id = db.add_experiment(
        name, author, repository, commit, diff, command, num_nodes
    )

    result = {"info": "launch experiment"}

    supervisors = db.lock_supervisors(experiment_id, num_nodes, cluster)

    if not supervisors:
        db.set_experiment_status(experiment_id, "ignored")

        if supervisors is None:
            result["error"] = f"Failed to lock {num_nodes} supervisors"
        else:
            result["error"] = "No available supervisors"

    else:
        db.set_experiment_status(experiment_id, "assigned")
        clients = [SupervisorClient(supervisor.endpoint) for supervisor in supervisors]
        results = [client.update() for client in clients]
        result["clients"] = [asdict(s) for s in supervisors]
        result["client_responses"] = results

    result["experiment"] = asdict(db.get_experiment(experiment_id))

    jasnah.log(result)

    return result


def run_server():
    app.run("0.0.0.0", 8100)


class ServerClient:
    def __init__(self, url):
        self.url = url
        self.conn = requests.Session()

    def status(self):
        result = self.conn.get(self.url + "/status")
        return result.json()

    def submit(
        self,
        name: str,
        repository: str,
        commit: str,
        command: str,
        diff: Optional[str] = None,
        author: Optional[str] = None,
        num_nodes=1,
        cluster="truthwatcher",
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
                num_nodes=num_nodes,
                cluster=cluster,
            ),
        )
        return result.json()


if __name__ == "__main__":
    client = ServerClient("http://127.0.0.1:8100")
    # print(client.status())
    import json

    print(
        json.dumps(
            client.submit(
                "test_experiment",
                "git@github.com:nearai/jasnah-cli.git",
                "b0dfca8637522eae9d20c5a7c2a843816b86ed87",
                "python3 examples/simple_task.py",
                num_nodes=2,
            )
        )
    )
