import json
import time
from pathlib import Path

LOG = Path.home() / '.local' / 'share' / 'ghost_night' / 'log.jsonl'


def event(kind, **kw):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'event': kind}
    rec.update({k: v for k, v in kw.items() if v is not None})
    with open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')


def tail(n=8):
    try:
        lines = LOG.read_text().strip().splitlines()
        return [json.loads(x) for x in lines[-n:]]
    except (FileNotFoundError, json.JSONDecodeError):
        return []
