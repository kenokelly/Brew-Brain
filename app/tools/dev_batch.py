"""
Dev batch: point Brew Brain at a Tilt sitting in water for development.

    docker exec brew-brain python -m tools.dev_batch start    # snapshot + switch
    docker exec brew-brain python -m tools.dev_batch status
    docker exec brew-brain python -m tools.dev_batch restore  # back to the snapshot

`start` saves the current batch settings to DATA_DIR/dev_batch_snapshot.json
(only if no snapshot exists, so re-running `start` to reset the clock never
overwrites the real batch), then sets a "DEV" batch with a compressed schedule:
four steps over 30 hours, so step changes, "next step in <24h" warnings and
the autopilot journal all fire in real time.

The real Tilt stream is untouched (no test_mode): gravity stays flat in
water, so the phase settles to STABLE. Use test_mode in Settings when you
need a simulated falling-gravity curve instead.
"""

import json
import os
import sys
from datetime import datetime, timezone

from core.config import DATA_DIR, get_config, set_config

SNAPSHOT = os.path.join(DATA_DIR, "dev_batch_snapshot.json")

# Keys the dev batch changes; exactly these are snapshotted and restored.
BATCH_KEYS = [
    "batch_name", "batch_notes", "style", "yeast_strain", "og", "target_fg",
    "start_date", "ferm_steps", "ferm_start", "target_temp", "brew_active",
    "yeast_min_temp", "yeast_max_temp", "yeast_attenuation", "yeast_flocculation",
]

DEV_STEPS = [
    {"name": "Primary", "type": "Primary", "temp": 20.0, "days": 0.25},
    {"name": "Secondary", "type": "Secondary", "temp": 22.0, "days": 0.25},
    {"name": "Soft Crash", "type": "Cold Crash", "temp": 10.0, "days": 0.25},
    {"name": "Cold Crash", "type": "Cold Crash", "temp": 2.0, "days": 0.5},
]


def start() -> None:
    if not os.path.exists(SNAPSHOT):
        with open(SNAPSHOT, "w") as f:
            json.dump({k: get_config(k) for k in BATCH_KEYS}, f, indent=2)
        print(f"Saved current batch '{get_config('batch_name')}' to {SNAPSHOT}")
    else:
        print(f"Snapshot already exists ({SNAPSHOT}); keeping it, resetting dev clock")

    now = datetime.now(timezone.utc)
    dev = {
        "batch_name": "DEV · Water test",
        "batch_notes": "Tilt in plain water for development. Restore with: python -m tools.dev_batch restore",
        "style": "Dev",
        "yeast_strain": "Unknown",
        "og": 1.000,
        "target_fg": 1.000,
        "start_date": now.strftime("%Y-%m-%d"),
        "ferm_steps": DEV_STEPS,
        "ferm_start": now.isoformat(),
        "target_temp": None,
        "yeast_min_temp": None,
        "yeast_max_temp": None,
        "yeast_attenuation": None,
        "yeast_flocculation": "",
        "brew_active": True,
    }
    for k, v in dev.items():
        set_config(k, v)
    print("Dev batch active: 4 steps over 30h starting now, Brew Active on.")


def restore() -> None:
    if not os.path.exists(SNAPSHOT):
        print("No snapshot found; nothing to restore.")
        sys.exit(1)
    with open(SNAPSHOT) as f:
        saved = json.load(f)
    for k in BATCH_KEYS:
        if k in saved:
            set_config(k, saved[k])
    os.remove(SNAPSHOT)
    print(f"Restored batch '{saved.get('batch_name')}' and removed the snapshot.")


def status() -> None:
    print(f"Batch: {get_config('batch_name')}  brew_active={get_config('brew_active')}  "
          f"steps={len(get_config('ferm_steps') or [])}  ferm_start={get_config('ferm_start')}")
    print(f"Snapshot: {'present' if os.path.exists(SNAPSHOT) else 'none'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"start": start, "restore": restore, "status": status}.get(cmd, status)()
