# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import re


class KitsuException(Exception, abc.ABC):
    @property
    @abc.abstractmethod
    def what(self) -> str:
        raise NotImplementedError()


RE_FILENAME_PROHIBITED = re.compile(r"[ _\\\n\t\r#\[\]{}<>^*/:`]+", flags=re.MULTILINE | re.IGNORECASE)


def fs_name_strip(name: str) -> str:
    return re.sub(RE_FILENAME_PROHIBITED, " ", name.replace(":", ".")).strip()
