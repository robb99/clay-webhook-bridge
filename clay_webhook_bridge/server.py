from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import subprocess

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class Settings:
    token: str
    log_path: Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_valid_token(settings: Settings, header_token: Optional[str], query_token: Optional[str]) -> bool:
    if not settings.token:
        return False
    if header_token and header_token == settings.token:
        return True
    if query_token and query_token == settings.token:
        return True
    return False


def build_event_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_type": body.get("event_type") or body.get("event") or "unknown",
        "source": body.get("source") or "home_assistant",
        "camera_entity": body.get("camera_entity"),
        "message": body.get("message") or body.get("description") or "",
        "ts": body.get("ts") or _utc_now_iso(),
    }


def build_wake_command(event_compact_json: str) -> list[str]:
    """Build a safe argv list to wake OpenClaw/Clawdbot via the Gateway.

    We use `clawdbot gateway call cron.wake` because the CLI does not expose a
    `wake` subcommand directly.
    """

    params = {
        "mode": "now",
        "text": f"HA_EVENT {event_compact_json}",
    }

    return [
        "clawdbot",
        "gateway",
        "call",
        "cron.wake",
        "--params",
        json.dumps(params, separators=(",", ":"), ensure_ascii=False),
    ]


def run_wake(cmd: list[str]) -> tuple[bool, Optional[str]]:
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            error_text = (completed.stderr or completed.stdout or "").strip()
            return False, error_text
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _json_compact(data: Dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def _write_jsonl(lock: threading.Lock, path: Path, record: Dict[str, Any]) -> None:
    line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI()
    log_lock = threading.Lock()

    @app.post("/webhook")
    async def webhook(request: Request) -> JSONResponse:
        received_at = _utc_now_iso()
        header_token = request.headers.get("X-Ping-Token")
        query_token = request.query_params.get("token")

        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("json is not an object")
        except Exception as exc:  # noqa: BLE001
            record = {
                "ts": received_at,
                "valid": False,
                "reason": "invalid_json",
                "error": str(exc),
                "remote": request.client.host if request.client else None,
            }
            _write_jsonl(log_lock, settings.log_path, record)
            return JSONResponse(status_code=400, content={"status": "error", "error": "invalid_json"})

        valid = is_valid_token(settings, header_token, query_token)
        if not valid:
            record = {
                "ts": received_at,
                "valid": False,
                "reason": "invalid_token",
                "remote": request.client.host if request.client else None,
                "body": body,
            }
            _write_jsonl(log_lock, settings.log_path, record)
            return JSONResponse(status_code=401, content={"status": "error", "error": "invalid_token"})

        event_payload = build_event_payload(body)
        compact_json = _json_compact(event_payload)
        cmd = build_wake_command(compact_json)

        result_ok, error_text = run_wake(cmd)

        record = {
            "ts": received_at,
            "valid": True,
            "remote": request.client.host if request.client else None,
            "body": body,
            "event": event_payload,
            "cmd": cmd,
            "ok": result_ok,
            "error": error_text,
        }
        _write_jsonl(log_lock, settings.log_path, record)

        status = "ok" if result_ok else "error"
        return JSONResponse(status_code=200 if result_ok else 502, content={"status": status})

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        return JSONResponse(content={"status": "ok", "ts": int(time.time())})

    return app
