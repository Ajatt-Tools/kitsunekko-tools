# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import asyncio
import time
import typing

from httpx import Headers


def parse_num(value: str) -> int | float:
    try:
        return int(value)
    except ValueError:
        return float(value)


def header_key_to_field_name(header_key: str) -> str:
    return header_key.replace("x-ratelimit-", "").replace("-", "_")


SLEEP_ENSURANCE_DELAY = 0.1


class RateLimit(typing.NamedTuple):
    # The number of requests that can be made.
    limit: int
    # How many requests are left before hitting a 429.
    remaining: int
    # The UNIX timestamp (seconds since midnight UTC on January 1st 1970) at which the rate limit resets.
    # This can have a fractional component for milliseconds.
    reset: int
    # The total time in seconds to wait for the rate limit to restart.
    # This can have a fractional component for milliseconds.
    reset_after: float | int = 0

    @classmethod
    def from_headers(cls, headers: Headers) -> typing.Self:
        return cls(
            **{
                header_key_to_field_name(key): parse_num(value)
                for key, value in headers.items()
                if key.startswith("x-ratelimit-")
            }
        )

    async def sleep(self):
        await asyncio.sleep(max(0, self.reset_after) + SLEEP_ENSURANCE_DELAY)


def main():
    headers = Headers(
        [
            ("content-type", "application/json"),
            ("access-control-allow-credentials", "true"),
            ("x-ratelimit-limit", "25"),
            ("x-ratelimit-remaining", "24"),
            ("x-ratelimit-reset", "1714518300"),
            ("vary", "origin, access-control-request-method, access-control-request-headers"),
            ("vary", "accept-encoding"),
            ("content-encoding", "gzip"),
            ("transfer-encoding", "chunked"),
            ("date", "Tue, 30 Apr 2024 23:04:52 GMT"),
        ]
    )
    print(RateLimit.from_headers(headers))


if __name__ == "__main__":
    main()
