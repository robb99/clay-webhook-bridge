from pathlib import Path
from unittest.mock import MagicMock, patch

from clay_webhook_bridge.server import Settings, build_wake_command, is_valid_token, run_wake


def test_is_valid_token_header_and_query():
    settings = Settings(token="secret", log_path=Path("/tmp/log.jsonl"))

    assert is_valid_token(settings, header_token="secret", query_token=None)
    assert is_valid_token(settings, header_token=None, query_token="secret")
    assert not is_valid_token(settings, header_token="wrong", query_token=None)
    assert not is_valid_token(settings, header_token=None, query_token="wrong")


def test_build_wake_command_compact_json():
    cmd = build_wake_command("{\"event_type\":\"x\"}")
    assert cmd[:4] == ["clawdbot", "gateway", "call", "cron.wake"]
    assert "--params" in cmd
    assert "--timeout" in cmd
    params = cmd[cmd.index("--params") + 1]
    assert "HA_EVENT" in params


def test_build_wake_command_with_gateway_overrides():
    cmd = build_wake_command(
        "{}",
        gateway_url="ws://127.0.0.1:1234",
        gateway_token="tok",
        gateway_timeout_ms=5000,
    )
    assert "--url" in cmd
    assert cmd[cmd.index("--url") + 1] == "ws://127.0.0.1:1234"
    assert "--token" in cmd
    assert cmd[cmd.index("--token") + 1] == "tok"
    assert cmd[cmd.index("--timeout") + 1] == "5000"


def test_run_wake_success_and_failure():
    ok_proc = MagicMock(returncode=0, stdout="", stderr="")
    fail_proc = MagicMock(returncode=2, stdout="oops", stderr="")

    with patch("clay_webhook_bridge.server.subprocess.run", return_value=ok_proc) as mocked:
        ok, err = run_wake(["clawdbot"])  # minimal
        assert ok is True
        assert err is None
        mocked.assert_called_once()

    with patch("clay_webhook_bridge.server.subprocess.run", return_value=fail_proc):
        ok, err = run_wake(["clawdbot"])  # minimal
        assert ok is False
        assert err == "oops"
