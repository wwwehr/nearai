from dataclasses import dataclass
from subprocess import run
from threading import Lock
from typing import Optional

from flask import Flask, request

app = Flask(__name__)

LOCK = Lock()
TASK = None


@app.route("/status")
def status():
    return f"Ok! task: {TASK}"


@dataclass
class TaskDescription:
    repository: str
    commit: str
    command: str
    diff: Optional[str] = None


@app.post("/submit")
def submit():
    global TASK

    locked = LOCK.acquire(blocking=False)

    if not locked:
        return f"There is a task already running! {TASK}"

    try:
        TASK = TaskDescription(**request.json)

        print("Start")
        print("End")
    except Exception as e:
        LOCK.release()
        raise e
    else:
        LOCK.release()
        return "ok"


def run_supervisor():
    app.run()
