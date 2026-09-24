#!/usr/bin/env python3
"""Assemble public/data/project-manifest.json from the per-project sources.

Sources of truth:
  content/site.json             site chrome, research themes, project order
  content/projects/<slug>.json  one file per project write-up

The assembled manifest is a build artifact and is not committed, so each
`kausar/<slug>` revision branch only ever touches a single file.

Usage:
  python3 tools/build_manifest.py            # build
  python3 tools/build_manifest.py --check    # validate only, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_FILE = ROOT / "content" / "site.json"
PROJECT_DIR = ROOT / "content" / "projects"
OUTPUT = ROOT / "public" / "data" / "project-manifest.json"
PAGE_DIR = ROOT / "public" / "projects"

REQUIRED_FIELDS = (
    "slug",
    "tier",
    "status",
    "title",
    "eyebrow",
    "headline",
    "summary",
    "problem",
    "contribution",
    "pipeline",
    "evidence",
    "limitations",
)
LIST_FIELDS = ("pipeline", "evidence")
VALID_TIERS = ("featured", "supporting")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"missing source file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def validate(project: Path, data: dict, expected_slug: str) -> list[str]:
    where = project.relative_to(ROOT)
    errors = []

    if data.get("slug") != expected_slug:
        errors.append(f"{where}: 'slug' must be \"{expected_slug}\"")
    if data.get("tier") not in VALID_TIERS:
        errors.append(f"{where}: 'tier' must be one of {VALID_TIERS}")

    for field in REQUIRED_FIELDS:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"{where}: '{field}' is missing or empty")
    for field in LIST_FIELDS:
        value = data.get(field)
        if value is not None and not isinstance(value, list):
            errors.append(f"{where}: '{field}' must be a list")

    if not (PAGE_DIR / expected_slug / "index.html").exists():
        errors.append(f"{where}: no page at public/projects/{expected_slug}/index.html")

    return errors


def build() -> tuple[dict, list[str]]:
    site = load_json(SITE_FILE)
    order = site.pop("projectOrder", None)
    if not order:
        raise SystemExit("content/site.json must define 'projectOrder'")

    on_disk = {path.stem for path in PROJECT_DIR.glob("*.json")}
    errors = []
    for extra in sorted(on_disk - set(order)):
        errors.append(f"content/projects/{extra}.json is not listed in projectOrder")

    projects = []
    for slug in order:
        path = PROJECT_DIR / f"{slug}.json"
        data = load_json(path)
        errors.extend(validate(path, data, slug))
        projects.append(data)

    manifest = {
        "site": site["site"],
        "researchThemes": site["researchThemes"],
        "projects": projects,
    }
    return manifest, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the sources without writing the manifest",
    )
    args = parser.parse_args()

    manifest, errors = build()
    if errors:
        print("Manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    count = len(manifest["projects"])
    if args.check:
        print(f"OK: {count} projects validated.")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({count} projects).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
