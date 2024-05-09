from pathlib import Path
from typing import List

from fabric import ThreadingGroup as Group

import jasnah


def parse_hosts(hosts_path: Path) -> List[str]:
    hosts = []
    with open(hosts_path) as f:
        for line in f:
            p = line.find("#")
            if p != -1:
                line = line[:p]
            line = line.strip(" \n")
            if not line:
                continue
            hosts.append(line)
    return hosts


def install(hosts: List[str]):
    """Install supervisor on every host."""
    hosts = Group(*hosts)

    # Check we have connection to every host
    result = hosts.run("hostname", hide=True, warn=False)
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, hostname: {stdout}")

    # Install setup_host.sh script
    setup_script = jasnah.etc("setup_host.sh")
    assert setup_script.exists(), setup_script
    hosts.put(setup_script, "/tmp/setup_host.sh")

    # Install supervisor
    hosts.run("bash /tmp/setup_host.sh", warn=False)


def start_server(hosts: Path):
    hosts = parse_hosts(hosts)
    install(hosts)
