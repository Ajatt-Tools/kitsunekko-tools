# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc

import httpx

from kitsunekko_tools.config import KitsuConfig


class KitsuException(Exception, abc.ABC):
    @abc.abstractmethod
    def what(self):
        raise NotImplementedError()


def get_http_client(config: KitsuConfig):
    return httpx.AsyncClient(
        proxies=config.proxy,
        headers=config.headers,
        timeout=config.timeout,
        follow_redirects=False,
    )
