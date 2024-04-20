# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import subprocess
import sys
from typing import Sequence

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig


@dataclasses.dataclass
class MegaError(KitsuException, RuntimeError):
    what: str


def raise_for_status(out: subprocess.CompletedProcess):
    if out.returncode != 0:
        raise MegaError(f"Command failed with code {out.returncode}")


def run(args: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args=args,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def mega_upload(config: KitsuConfig):
    remote_destination = f"/Root/{config.destination.name}"
    print(f"Remote destination: {remote_destination}")
    out = run(
        args=("megamkdir", remote_destination),
    )
    raise_for_status(out)
    out = run(
        args=("megacopy", "--local", config.destination, "--remote", remote_destination, "--no-follow"),
    )
    raise_for_status(out)
