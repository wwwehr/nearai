import shlex
import tempfile
from dataclasses import dataclass
from subprocess import run
from threading import Lock
from typing import Optional

import requests
from flask import Flask, request

import jasnah
import jasnah.config

app = Flask(__name__)

REPOSITORIES = jasnah.config.DATA_FOLDER / "repositories"
LOCK = Lock()
TASK: Optional["TaskDescription"] = None


@app.route("/status")
def status():
    return f"Ok! task: {TASK}\n"


@dataclass
class TaskDescription:
    repository: str
    commit: str
    command: str
    diff: Optional[str] = None


def repository_name(repository):
    return repository.split("/")[-1]


@app.post("/submit")
def submit():
    global TASK

    locked = LOCK.acquire(blocking=False)

    def teardown():
        TASK = None
        LOCK.release()

    if not locked:
        return f"There is a task already running! {TASK}"

    try:
        # TODO: Read task from the database instead
        TASK = TaskDescription(**request.json)

        # Clone the repository via ssh instead of https to avoid password prompts
        assert TASK.repository.startswith("git@")

        name = repository_name(TASK.repository)
        repository_path = REPOSITORIES / name

        if not repository_path.exists():
            run(["git", "clone", TASK.repository, repository_path])

        run(["git", "pull"], cwd=repository_path)
        run(["git", "reset", "--hard"], cwd=repository_path)
        run(["git", "checkout", TASK.commit], cwd=repository_path)

        if TASK.diff:
            with tempfile.NamedTemporaryFile("w") as f:
                f.write(TASK.diff)
                run(["git", "apply", f.name], cwd=repository_path)

        command = shlex.split(TASK.command)
        run(command, cwd=repository_path)

    except Exception as e:
        teardown()
        raise e
    else:
        teardown()
        return "ok"


def run_supervisor():
    app.run("0.0.0.0", 8000)


class SupervisorClient:
    def __init__(self, url):
        self.url = url
        self.conn = requests.Session()

    def status(self):
        result = self.conn.get(self.url + "/status")
        print(result.text)

    def submit(
        self, repository: str, commit: str, command: str, diff: Optional[str] = None
    ):
        result = self.conn.post(
            self.url + "/submit",
            json=dict(repository=repository, commit=commit, command=command, diff=diff),
        )
        print(result)
        return "Supervisor Ok"


if __name__ == "__main__":
    client = SupervisorClient("http://10.141.0.13:8000")
    client.status()
    client.submit(
        "git@github.com:nearai/jasnah-cli.git",
        "d215f25fdd3e56ccb802e72a9481ffc240c13643",
        "python3 examples/simple_task.py",
    )
