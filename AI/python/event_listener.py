import datetime
import json
import sys


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


print(f"[{now_str()}] Python event listener started", flush=True)

for raw_line in sys.stdin:
    line = raw_line.strip()
    if not line:
        continue

    try:
        event = json.loads(line)
    except Exception as exc:
        print(f"[{now_str()}] parse_error: {exc} line={line}", flush=True)
        continue

    event_name = event.get("event", "unknown")
    frame = event.get("frame", -1)
    payload = event.get("payload", {})

    print(f"[{now_str()}] event={event_name} frame={frame} payload={payload}", flush=True)

    if event_name == "shutdown":
        break

print(f"[{now_str()}] Python event listener stopped", flush=True)
