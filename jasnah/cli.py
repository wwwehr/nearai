from pathlib import Path

import fire

from jasnah import registry
from jasnah.server import start_server
from jasnah.supervisor import run_supervisor


class RegistryCli:
    def __init__(self, registry: registry.Registry):
        self._registry = registry

    def list(self):
        """List available items"""
        self._registry.list()

    def upload(self, path: str, name: str):
        """Upload item"""
        self._registry.upload(Path(path), name)

    def get(self, name: str):
        """Download item"""
        self._registry.download(name)


class SupervisorCli:
    def start(self):
        # Install service if it hasn't been installed before
        # Start service
        pass

    def run(self):
        run_supervisor()


class CLI:
    def __init__(self):
        self.dataset = RegistryCli(registry.dataset)
        self.model = RegistryCli(registry.model)
        self.supervisor = SupervisorCli()

    def server(self, hosts: str):
        """Start controller server"""
        hosts = Path(hosts)
        start_server(hosts)

    def run(self):
        """Submit task"""
        raise NotImplementedError()

    def inference(self):
        """Run inference task"""
        raise NotImplementedError()

    def config(self):
        """Configure jasnah-cli settings"""
        # TODO: Host, database url, author
        raise NotImplementedError()


def main():
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
