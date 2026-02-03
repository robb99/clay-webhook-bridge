# clay-webhook-bridge

Event-driven Home Assistant -> OpenClaw bridge. Receives POST webhooks, validates a shared token, and calls `clawdbot gateway call cron.wake` with a compact JSON payload. All requests (valid and invalid) are logged to a JSONL file.

## Requirements
- Python 3.10+ (works with 3.8+ but 3.10+ recommended)
- `clawdbot` available in PATH on the VM

## Install (Ubuntu VM)
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv

sudo mkdir -p /opt/clay-webhook-bridge
sudo chown $USER:$USER /opt/clay-webhook-bridge

cd /opt/clay-webhook-bridge
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run (CLI)
```bash
export CLAY_WEBHOOK_TOKEN="your-shared-token"
python -m clay_webhook_bridge --host 0.0.0.0 --port 8789 --token-env CLAY_WEBHOOK_TOKEN --log /var/log/clay-webhook-bridge.jsonl
```

## Test with curl
```bash
export CLAY_WEBHOOK_TOKEN="your-shared-token"

curl -X POST "http://127.0.0.1:8789/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Ping-Token: $CLAY_WEBHOOK_TOKEN" \
  -d '{"event_type":"test","source":"home_assistant","message":"hello"}'
```

## Systemd (example)
See `examples/systemd/clay-webhook-bridge.service` for a unit file. Edit the `User`, `WorkingDirectory`, and `Environment` values to match your VM.

Typical setup:
```bash
sudo cp examples/systemd/clay-webhook-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable clay-webhook-bridge
sudo systemctl restart clay-webhook-bridge
sudo systemctl status clay-webhook-bridge
```

## Home Assistant examples
See `examples/home_assistant.yaml` for `rest_command` + automation samples. Make sure the `X-Ping-Token` header matches the shared token.

## Logs
Every request is written to a JSONL file (valid and invalid). Each line includes timestamp, validation result, and either the error or the command + event payload.

## Tests
```bash
pytest
```
