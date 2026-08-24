# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from kitsunekko_tools.api_access.download import (
    ApiBadStatusError,
    ApiRateLimitedError,
    ApiResponseCode,
)
from kitsunekko_tools.api_access.rate_limit import RateLimit
from kitsunekko_tools.common import KitsuError, KitsuException
from kitsunekko_tools.config import (
    ConfigFileInvalidError,
    ConfigFileNotFoundError,
    DestDirNotFoundError,
)
from kitsunekko_tools.file_downloader import KitsuConnectionError
from kitsunekko_tools.ignore import IgnoreListException
from kitsunekko_tools.mega_upload import MegaError


@pytest.mark.parametrize(
    "exception",
    [
        ApiBadStatusError(ApiResponseCode.entry_not_found),
        ApiRateLimitedError(ApiResponseCode.rate_limit_exceeded, RateLimit(limit=25, remaining=0, reset=0)),
        KitsuError("test error"),
        ConfigFileNotFoundError(),
        DestDirNotFoundError("missing destination"),
        ConfigFileInvalidError("invalid config"),
        KitsuConnectionError("https://example.com/subtitle.srt"),
        IgnoreListException("invalid ignore list"),
        MegaError("upload failed"),
    ],
    ids=lambda exception: type(exception).__name__,
)
def test_dataclass_exceptions_accept_traceback_state(exception: KitsuException) -> None:
    """Dataclass exceptions must remain mutable so Python can attach traceback and chaining state."""
    note = "additional exception context"
    cause = RuntimeError("underlying failure")

    exception.add_note(note)
    with pytest.raises(type(exception)) as raised:
        # Raising mutates exception internals, which is why exception dataclasses cannot be frozen.
        raise exception from cause

    assert raised.value is exception
    assert raised.value.__notes__ == [note]
    assert raised.value.__cause__ is cause
    assert raised.value.__traceback__ is not None
