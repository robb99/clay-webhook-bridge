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
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    token = os.environ.get(args.token_env, "")
    settings = Settings(token=token, log_path=Path(args.log))

    app = create_app(settings)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
