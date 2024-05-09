import shlex
import tempfile
from dataclasses import dataclass
from subprocess import run
from threading import Lock
from typing import Optional

from flask import Flask, request

import jasnah
import jasnah.config

app = Flask(__name__)

REPOSITORIES = jasnah.config.DATA_FOLDER / "repositories"
LOCK = Lock()
TASK: Optional["TaskDescription"] = None


@app.route("/status")
def status():
    return f"Ok! task: {TASK}"


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
            run_supervisor(["git", "clone", TASK.repository, repository_path])

        run_supervisor(["git", "reset", "--hard"], cwd=repository_path)
        run_supervisor(["git", "checkout", TASK.commit], cwd=repository_path)

        if TASK.diff:
            with tempfile.NamedTemporaryFile("w") as f:
                f.write(TASK.diff)
                run_supervisor(["git", "apply", f.name], cwd=repository_path)

        command = shlex.split(TASK.command)
        run_supervisor(command, cwd=repository_path)

    except Exception as e:
        LOCK.release()
        raise e
    else:
        LOCK.release()
        return "ok"


def run_supervisor():
    app.run("0.0.0.0", 8000)
