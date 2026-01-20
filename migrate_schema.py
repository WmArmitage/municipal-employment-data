#!/usr/bin/env python3
"""
migrate_schema.py

One-time migration to make the dataset self-healing:
- Ensures Town Website points to homepage.
- Freezes original URLs into "(original)" fields.
- Does NOT remove/rename existing keys.

Usage:
  python migrate_schema.py CT_Municipal_Employment_Pages.json CT_Municipal_Employment_Pages.migrated.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def homepage_from_url(url: str) -> Optional[str]:
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        u = urlparse(url.strip())
        if not u.scheme or not u.netloc:
            return None
        return f"{u.scheme}://{u.netloc}/"
    except Exception:
        return None


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python migrate_schema.py <input.json> <output.json>")
        return 2

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    data = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected input JSON to be a list (array) of objects.")

    changed = 0
    for rec in data:
        if not isinstance(rec, dict):
            continue

        # Ensure Town Website is homepage.
        town_site = rec.get("Town Website")
        home = homepage_from_url(town_site) if isinstance(town_site, str) else None

        # If Town Website is missing or not a clean homepage, derive from employment URL first, then application URL.
        if not home:
            emp = rec.get("Employment Page URL")
            app = rec.get("Application Form URL")
            home = homepage_from_url(emp) or homepage_from_url(app)

        if home and rec.get("Town Website") != home:
            rec["Town Website"] = home
            changed += 1

        # Freeze originals (immutable)
        if "Employment Page URL (original)" not in rec and isinstance(rec.get("Employment Page URL"), str):
            rec["Employment Page URL (original)"] = rec["Employment Page URL"]
            changed += 1

        if "Application Form URL (original)" not in rec and isinstance(rec.get("Application Form URL"), str):
            rec["Application Form URL (original)"] = rec["Application Form URL"]
            changed += 1

    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done. Wrote {out_path}. Records updated: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
