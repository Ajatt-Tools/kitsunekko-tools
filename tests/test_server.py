# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import pathlib
import subprocess
import urllib.request
from collections.abc import Sequence
from unittest.mock import create_autospec, patch

import fire
import pytest

from kitsunekko_tools.__main__ import Application
from kitsunekko_tools.common import KitsuError
from kitsunekko_tools.config import Config, KitsuConfig
from kitsunekko_tools.consts import (
    DEFAULT_SERVER_BIND_ADDRESS,
    DEFAULT_SERVER_BIND_PORT,
)
from kitsunekko_tools.server import (
    make_server,
    open_page_in_browser,
    serve_site,
    server_browser_url,
    server_config,
    system_browser,
)
from kitsunekko_tools.website.context import make_site_dir_path
from tests.helpers import (
    make_server_config,
    mock_catalog_server,
    running_catalog_server,
)


class TestBrowser:
    """Verify browser selection, argument handling, and advisory startup failures."""

    @pytest.mark.parametrize("browser,expected", [(None, "xdg-open"), ("", "xdg-open"), ("firefox", "firefox")])
    def test_system_browser(self, monkeypatch: pytest.MonkeyPatch, browser: str | None, expected: str) -> None:
        """Unset and empty browser settings fall back to xdg-open."""
        if browser is None:
            monkeypatch.delenv("BROWSER", raising=False)
        else:
            monkeypatch.setenv("BROWSER", browser)
        assert system_browser() == expected

    @pytest.mark.parametrize(
        "browser,expected_args",
        [
            ("firefox", ("firefox",)),
            ("firefox --new-window", ("firefox", "--new-window")),
            ('"/opt/my browser" --profile "my profile"', ("/opt/my browser", "--profile", "my profile")),
            ("firefox ';echo not-a-command'", ("firefox", ";echo not-a-command")),
        ],
    )
    def test_launch(self, monkeypatch: pytest.MonkeyPatch, browser: str, expected_args: Sequence[str]) -> None:
        """Launch detached browsers with quoted arguments but no shell evaluation."""
        monkeypatch.setenv("BROWSER", browser)
        with patch("kitsunekko_tools.server.subprocess.Popen", autospec=True) as popen:
            open_page_in_browser("http://127.0.0.1:8801/")
        popen.assert_called_once_with(
            (*expected_args, "http://127.0.0.1:8801/"),
            stderr=subprocess.STDOUT,
            stdout=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,
        )

    @pytest.mark.parametrize("error", [FileNotFoundError("not found"), PermissionError("permission denied")])
    def test_startup_failure(self, capsys: pytest.CaptureFixture[str], error: OSError) -> None:
        """Browser startup failures emit warnings instead of aborting the preview."""
        with patch("kitsunekko_tools.server.subprocess.Popen", autospec=True, side_effect=error):
            assert open_page_in_browser("http://127.0.0.1:8801/") is None
        assert capsys.readouterr().err == f"Warning: could not open the browser: {error}\n"

    @pytest.mark.parametrize("browser", ['firefox "unfinished', "'unfinished"])
    def test_malformed_arguments(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], browser: str
    ) -> None:
        """Malformed quoting is advisory and never starts a subprocess."""
        monkeypatch.setenv("BROWSER", browser)
        with patch("kitsunekko_tools.server.subprocess.Popen", autospec=True) as popen:
            assert open_page_in_browser("http://127.0.0.1:8801/") is None
        popen.assert_not_called()
        assert capsys.readouterr().err == "Warning: could not open the browser: No closing quotation\n"


class TestServerConfig:
    """Verify configuration loading, immutable overrides, and shared catalog paths."""

    @pytest.mark.parametrize(
        "config_data,expected_address,expected_port",
        [
            ("", DEFAULT_SERVER_BIND_ADDRESS, DEFAULT_SERVER_BIND_PORT),
            ('server_bind_address = "0.0.0.0"\nserver_bind_port = 9000\n', "0.0.0.0", 9000),
        ],
    )
    def test_load(self, tmp_path: pathlib.Path, config_data: str, expected_address: str, expected_port: int) -> None:
        """Read server settings from TOML with defaults for omitted values."""
        config_path = tmp_path / "ktools.toml"
        config_path.write_text(config_data, encoding="utf-8")
        with config_path.open("rb") as config_file:
            config = KitsuConfig.from_file(config_file)
        assert (config.server_bind_address, config.server_bind_port) == (expected_address, expected_port)

    @pytest.mark.parametrize(
        "address,port,expected_address,expected_port",
        [
            (None, None, "127.0.0.2", 9010),
            ("0.0.0.0", None, "0.0.0.0", 9010),
            (None, 0, "127.0.0.2", 0),
            ("127.0.0.1", 9000, "127.0.0.1", 9000),
        ],
    )
    def test_overrides(
        self, tmp_path: pathlib.Path, address: str | None, port: int | None, expected_address: str, expected_port: int
    ) -> None:
        """Each command override replaces only its own setting without modifying the source."""
        config = dataclasses.replace(
            make_server_config(tmp_path), server_bind_address="127.0.0.2", server_bind_port=9010
        )
        result = server_config(config, address=address, port=port)
        assert (result.server_bind_address, result.server_bind_port) == (expected_address, expected_port)
        assert (config.server_bind_address, config.server_bind_port) == ("127.0.0.2", 9010)

    @pytest.mark.parametrize("destination", ["subtitles", "nested/subtitles", "nested/../subtitles"])
    def test_paths(self, tmp_path: pathlib.Path, destination: str) -> None:
        """Resolve the generated catalog beside the configured mirror."""
        config = dataclasses.replace(make_server_config(tmp_path), destination=tmp_path / destination)
        assert config.work_root == config.destination.resolve().parent
        assert make_site_dir_path(config) == config.work_root / "_site"


class TestListener:
    """Verify actual listener endpoints, HTTP responses, and unsupported addresses."""

    @pytest.mark.parametrize("address", ["::1", "::", "[::1]", "::ffff:127.0.0.1"])
    def test_reject_ipv6(self, tmp_path: pathlib.Path, address: str) -> None:
        """Reject IPv6 before attempting to construct an IPv4 listener."""
        config = server_config(make_server_config(tmp_path), address=address)
        with patch("kitsunekko_tools.server.http.server.ThreadingHTTPServer", autospec=True) as factory:
            with pytest.raises(KitsuError, match="supports IPv4 only"):
                make_server(config)
        factory.assert_not_called()

    @pytest.mark.parametrize("address", ["127.0.0.1", "0.0.0.0", "localhost"])
    def test_serve_content(self, tmp_path: pathlib.Path, address: str) -> None:
        """Fetch generated catalog content through a real ephemeral IPv4 listener."""
        config = server_config(make_server_config(tmp_path), address=address, port=0)
        make_site_dir_path(config).mkdir()
        make_site_dir_path(config).joinpath("index.html").write_text("<h1>Catalog preview</h1>", encoding="utf-8")
        with running_catalog_server(config) as server:
            assert server.server_port > 0
            assert server_browser_url(server) == f"http://127.0.0.1:{server.server_port}/"
            # Bypass ambient proxies so this test always contacts the local listener directly.
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                server_browser_url(server), timeout=5
            ) as response:
                assert response.status == 200
                assert response.read() == b"<h1>Catalog preview</h1>"
        assert server.socket.fileno() == -1


class TestServerLifecycle:
    """Verify preview startup, browser options, and cleanup on every exit path."""

    @pytest.mark.parametrize("launch_browser", [True, False])
    def test_serve(self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str], launch_browser: bool) -> None:
        """Apply overrides before binding and navigate to the actual listener URL."""
        config = make_server_config(tmp_path)
        server = mock_catalog_server()
        with (
            patch("kitsunekko_tools.server.make_server", autospec=True, return_value=server) as factory,
            patch("kitsunekko_tools.server.open_page_in_browser", autospec=True) as browser,
        ):
            serve_site(config, address="0.0.0.0", port=0, launch_browser=launch_browser)
        factory.assert_called_once_with(server_config(config, address="0.0.0.0", port=0))
        assert browser.call_args_list == ([(("http://127.0.0.1:49152/",), {})] if launch_browser else [])
        server.serve_forever.assert_called_once_with()
        server.server_close.assert_called_once_with()
        assert capsys.readouterr().out == f"Serving {tmp_path / '_site'} at http://127.0.0.1:49152/\nServer stopped.\n"

    @pytest.mark.parametrize("error", [KeyboardInterrupt(), RuntimeError("serving failed")])
    def test_cleanup_on_error(self, tmp_path: pathlib.Path, error: BaseException) -> None:
        """Close interrupted and failed listeners, propagating unexpected errors."""
        server = mock_catalog_server()
        server.serve_forever.side_effect = error
        with patch("kitsunekko_tools.server.make_server", autospec=True, return_value=server):
            if isinstance(error, KeyboardInterrupt):
                serve_site(make_server_config(tmp_path), launch_browser=False)
            else:
                with pytest.raises(RuntimeError, match="serving failed"):
                    serve_site(make_server_config(tmp_path), launch_browser=False)
        server.server_close.assert_called_once_with()

    @pytest.mark.parametrize("error", [FileNotFoundError("missing browser"), PermissionError("not executable")])
    def test_browser_failure_does_not_stop_serving(self, tmp_path: pathlib.Path, error: OSError) -> None:
        """Continue serving after an advisory browser startup failure."""
        server = mock_catalog_server()
        with (
            patch("kitsunekko_tools.server.make_server", autospec=True, return_value=server),
            patch("kitsunekko_tools.server.subprocess.Popen", autospec=True, side_effect=error),
        ):
            serve_site(make_server_config(tmp_path))
        server.serve_forever.assert_called_once_with()
        server.server_close.assert_called_once_with()


class TestServerCommand:
    """Verify Fire parses real command-line server options."""

    @pytest.mark.parametrize(
        "arguments,address,port,launch_browser",
        [
            (["server"], None, None, True),
            (["server", "--no-browser"], None, None, False),
            (["server", "--address=0.0.0.0", "--port=0", "--no-browser"], "0.0.0.0", 0, False),
        ],
    )
    def test_options(
        self,
        tmp_path: pathlib.Path,
        arguments: Sequence[str],
        address: str | None,
        port: int | None,
        launch_browser: bool,
    ) -> None:
        """Forward parsed CLI options to the preview server."""
        application = Application()
        config = create_autospec(Config, instance=True)
        config.data.return_value = make_server_config(tmp_path)
        application._config = config
        with patch("kitsunekko_tools.__main__.serve_site", autospec=True) as serve:
            fire.Fire(application, command=list(arguments))
        serve.assert_called_once_with(
            config.data.return_value, address=address, port=port, launch_browser=launch_browser
        )
