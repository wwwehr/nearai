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

    assert request.json is not None
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
        name=name, author=author, repository=repository, commit=commit, diff=diff, command=command, num_nodes=num_nodes
    )

    result = {}

    supervisors = db.lock_supervisors(experiment_id=experiment_id, total=num_nodes, cluster=cluster)

    if not supervisors:
        db.set_experiment_status(experiment_id=experiment_id, status="ignored")

        if supervisors is None:
            result["error"] = f"Failed to lock {num_nodes} supervisors"
        else:
            result["error"] = "No available supervisors"

    else:
        db.set_experiment_status(experiment_id=experiment_id, status="assigned")
        clients = [SupervisorClient(supervisor.endpoint) for supervisor in supervisors]
        results = [client.update() for client in clients]
        result["clients"] = [asdict(s) for s in supervisors]
        result["client_responses"] = results

    experiment = db.get_experiment(experiment_id)
    assert experiment is not None
    result["experiment"] = asdict(experiment)

    jasnah.log(target="launch experiment", **result)

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
        author: str,
        diff: Optional[str] = None,
        num_nodes=1,
        cluster="truthwatcher",
    ):
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
