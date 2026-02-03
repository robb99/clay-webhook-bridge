from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from .server import Settings, create_app


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Home Assistant -> OpenClaw webhook bridge")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8789, help="Port to bind")
    parser.add_argument("--token-env", default="CLAY_WEBHOOK_TOKEN", help="Env var name for shared token")
    parser.add_argument("--log", default="./clay-webhook-bridge.jsonl", help="JSONL log file path")

    parser.add_argument("--gateway-url", default=None, help="Gateway WebSocket URL (optional override)")
    parser.add_argument(
        "--gateway-token-env",
        default="CLAWDBOT_GATEWAY_TOKEN",
        help="Env var name for the gateway token (optional)",
    )
    parser.add_argument("--gateway-timeout-ms", type=int, default=10000, help="Gateway call timeout (ms)")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    token = os.environ.get(args.token_env, "")
    gateway_token = os.environ.get(args.gateway_token_env, "") or None

    settings = Settings(
        token=token,
        log_path=Path(args.log),
        gateway_url=args.gateway_url,
        gateway_token=gateway_token,
        gateway_timeout_ms=args.gateway_timeout_ms,
    )

    app = create_app(settings)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
