from typing import Optional

import requests


class SupervisorClient:
    def __init__(self, ip, port=8000):
        self.url = f"http://{ip}:{port}"
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


if __name__ == "__main__":
    client = SupervisorClient("10.141.0.11")
    client.status()
    client.submit(
        "git@github.com:JasnahOrg/jasnah-cli.git",
        "d215f25fdd3e56ccb802e72a9481ffc240c13643",
        "python3 examples/simple_task.py",
    )
