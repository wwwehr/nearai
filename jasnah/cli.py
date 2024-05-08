from pathlib import Path

import fire

from jasnah import registry


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


class CLI:
    def __init__(self):
        self.dataset = RegistryCli(registry.dataset)
        self.model = RegistryCli(registry.model)

    def server(self):
        """Start server"""
        raise NotImplementedError()

    def run(self):
        """Submit task"""
        raise NotImplementedError()

    def inference(self):
        """Run inference task"""

    def config(self):
        """Configure jasnah-cli settings"""
        # TODO: Host, database url, author


def main():
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
