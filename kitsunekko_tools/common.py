# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc


class KitsuException(Exception, abc.ABC):
    @property
    @abc.abstractmethod
    def what(self) -> str:
        raise NotImplementedError()
