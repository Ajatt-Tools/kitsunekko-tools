# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import subprocess
import sys

from kitsunekko_tools.common import KitsuException
from kitsunekko_tools.config import KitsuConfig


@dataclasses.dataclass(frozen=True)
class MegaError(KitsuException, RuntimeError):
    what: str


def raise_for_status(out: subprocess.CompletedProcess):
    if out.returncode != 0:
        raise MegaError(f"Command failed with code {out.returncode}")


def mega_upload(config: KitsuConfig):
    remote_destination = f"/Root/{config.destination.name}"
    print(f"Remote destination: {remote_destination}")

    subprocess.run(  # will return 1 if directory already exists.
        args=("megamkdir", remote_destination),
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=False,
    )

    out = subprocess.run(
        args=("megacopy", "--local", config.destination, "--remote", remote_destination, "--no-follow"),
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=False,
    )
    raise_for_status(out)
