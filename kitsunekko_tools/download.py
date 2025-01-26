# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import abc
import enum

from kitsunekko_tools.config import KitsuConfig


@enum.unique
class ClientType(enum.Enum):
    api = enum.auto()
    kitsu_scrapper = enum.auto()


class ClientBase(abc.ABC):
    @abc.abstractmethod
    async def sync_all(self) -> None:
        raise NotImplementedError()
