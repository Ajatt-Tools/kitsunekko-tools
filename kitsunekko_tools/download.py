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
    _subclasses_map: dict[ClientType, type["ClientBase"]] = {}  # "api" -> ApiSyncClient

    def __init_subclass__(cls, **kwargs) -> None:
        # "type" is one of ("api", "kitsu_scrapper")
        client_type: ClientType = kwargs.pop("client_type")  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[client_type] = cls

    def __new__(cls, **kwargs) -> "ClientBase":
        subclass = cls._subclasses_map[kwargs["client_type"]]
        return object.__new__(subclass)

    def __init__(self, client_type: ClientType, config: KitsuConfig, full_sync: bool = False) -> None:
        pass

    @abc.abstractmethod
    async def sync_all(self) -> None:
        raise NotImplementedError()
