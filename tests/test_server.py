# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import functools
import http.server
import pathlib
import subprocess
from unittest.mock import create_autospec, patch

import pytest

from kitsunekko_tools.__main__ import Application
from kitsunekko_tools.config import Config, KitsuConfig
from kitsunekko_tools.consts import (
    DEFAULT_SERVER_BIND_ADDRESS,
    DEFAULT_SERVER_BIND_PORT,
)
from kitsunekko_tools.server import make_server, open_page_in_browser, serve_site, server_config, system_browser


def make_config(tmp_path: pathlib.Path) -> KitsuConfig:
    """Create a catalog configuration rooted in a temporary directory."""
    return dataclasses.replace(KitsuConfig.default(), destination=tmp_path / "subtitles")


@pytest.mark.parametrize("configured_browser,expected", [(None, "xdg-open"), ("firefox", "firefox")])
def test_system_browser(monkeypatch: pytest.MonkeyPatch, configured_browser: str | None, expected: str) -> None:
    """The browser command uses $BROWSER when configured and otherwise uses xdg-open."""
    if configured_browser is None:
        monkeypatch.delenv("BROWSER", raising=False)
    else:
        monkeypatch.setenv("BROWSER", configured_browser)

    assert system_browser() == expected


@pytest.mark.parametrize(
    "config_data, expected_address, expected_port",
    [
        ("", DEFAULT_SERVER_BIND_ADDRESS, DEFAULT_SERVER_BIND_PORT),
        ('server_bind_address = "0.0.0.0"\nserver_bind_port = 9000\n', "0.0.0.0", 9000),
    ],
    ids=["defaults", "configured_values"],
)
def test_kitsu_config_reads_server_settings(
    tmp_path: pathlib.Path, config_data: str, expected_address: str, expected_port: int
) -> None:
    """Server settings read from TOML replace the default local listener settings."""
    config_path = tmp_path / "ktools.toml"
    config_path.write_text(config_data, encoding="utf-8")
    with config_path.open("rb") as config_file:
        config = KitsuConfig.from_file(config_file)

    assert config.server_bind_address == expected_address
    assert config.server_bind_port == expected_port


@pytest.mark.parametrize("browser,url", [("firefox", "http://127.0.0.1:8801/")])
def test_open_page_in_browser(monkeypatch: pytest.MonkeyPatch, browser: str, url: str) -> None:
    """The browser is launched as a detached subprocess with output suppressed."""
    monkeypatch.setenv("BROWSER", browser)
    with patch("kitsunekko_tools.server.subprocess.Popen", autospec=True) as popen:
        open_page_in_browser(url)

    popen.assert_called_once_with(
        (browser, url),
        stderr=subprocess.STDOUT,
        stdout=subprocess.DEVNULL,
        shell=False,
        start_new_session=True,
    )


@pytest.mark.parametrize("browser_error", [OSError("browser command not found")])
def test_open_page_in_browser_warns_when_browser_is_unavailable(
    capsys: pytest.CaptureFixture[str], browser_error: OSError
) -> None:
    """A missing browser emits a warning instead of preventing the server from starting."""
    with patch("kitsunekko_tools.server.subprocess.Popen", autospec=True, side_effect=browser_error):
        assert open_page_in_browser("http://127.0.0.1:8801/") is None

    assert capsys.readouterr().err == f"Warning: could not open the browser: {browser_error}\n"


@pytest.mark.parametrize(
    "address, port, expected_address, expected_port",
    [
        (None, None, DEFAULT_SERVER_BIND_ADDRESS, DEFAULT_SERVER_BIND_PORT),
        ("0.0.0.0", 9000, "0.0.0.0", 9000),
    ],
    ids=["config_defaults", "command_overrides"],
)
def test_server_config_applies_optional_command_overrides(
    tmp_path: pathlib.Path,
    address: str | None,
    port: int | None,
    expected_address: str,
    expected_port: int,
) -> None:
    """Command options replace only the configured network settings they provide."""
    config = make_config(tmp_path)
    result = server_config(config, address=address, port=port)

    assert result.server_bind_address == expected_address
    assert result.server_bind_port == expected_port
    assert result.server_url == f"http://{expected_address}:{expected_port}/"
    assert config.server_bind_address == DEFAULT_SERVER_BIND_ADDRESS
    assert config.server_bind_port == DEFAULT_SERVER_BIND_PORT


@pytest.mark.parametrize("directory_name", ["_site"], ids=["generated_catalog"])
def test_make_server_serves_generated_catalog(directory_name: str, tmp_path: pathlib.Path) -> None:
    """The threaded HTTP server receives the generated catalog directory."""
    config = make_config(tmp_path)
    expected_directory = config.destination.parent / directory_name

    with patch(
        "kitsunekko_tools.server.http.server.ThreadingHTTPServer",
        return_value=create_autospec(http.server.ThreadingHTTPServer, instance=True),
    ) as http_server:
        make_server(config)

    handler = http_server.call_args.kwargs["RequestHandlerClass"]
    assert http_server.call_args.kwargs["server_address"] == (DEFAULT_SERVER_BIND_ADDRESS, DEFAULT_SERVER_BIND_PORT)
    assert isinstance(handler, functools.partial)
    assert handler.func is http.server.SimpleHTTPRequestHandler
    assert handler.keywords == {"directory": expected_directory}


@pytest.mark.parametrize(
    "serve_error,launch_browser,expected_browser_calls,expected_suffix",
    [
        (None, True, 1, "Server stopped.\n"),
        (KeyboardInterrupt(), True, 1, "\nKeyboard interrupt.\nServer stopped.\n"),
        (None, False, 0, "Server stopped.\n"),
    ],
)
def test_serve_site_closes_server(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    serve_error: BaseException | None,
    launch_browser: bool,
    expected_browser_calls: int,
    expected_suffix: str,
) -> None:
    """The development server closes after normal completion or a keyboard interrupt."""
    config = make_config(tmp_path)
    http_server = create_autospec(http.server.ThreadingHTTPServer, instance=True)
    http_server.serve_forever.side_effect = serve_error

    with (
        patch("kitsunekko_tools.server.make_server", autospec=True, return_value=http_server) as server_factory,
        patch("kitsunekko_tools.server.open_page_in_browser") as open_browser,
    ):
        serve_site(config, launch_browser=launch_browser)

    server_factory.assert_called_once_with(config)
    assert open_browser.call_count == expected_browser_calls
    if launch_browser:
        open_browser.assert_called_once_with(config.server_url)
    http_server.serve_forever.assert_called_once_with()
    http_server.server_close.assert_called_once_with()
    assert capsys.readouterr().out == f"Serving {tmp_path / '_site'} at {config.server_url}\n{expected_suffix}"


@pytest.mark.parametrize(
    "address,port,no_browser,launch_browser",
    [(None, None, False, True), ("0.0.0.0", 9000, True, False)],
)
def test_application_server_forwards_command_options(
    tmp_path: pathlib.Path,
    address: str | None,
    port: int | None,
    no_browser: bool,
    launch_browser: bool,
) -> None:
    """The Fire command forwards one-run overrides to the server module."""
    application = Application()
    config = create_autospec(Config, instance=True)
    config.data.return_value = make_config(tmp_path)
    application._config = config

    with patch("kitsunekko_tools.__main__.serve_site") as serve:
        application.server(address, port, no_browser)

    serve.assert_called_once_with(
        config.data.return_value,
        address=address,
        port=port,
        launch_browser=launch_browser,
    )
