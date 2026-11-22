#!/usr/bin/env python3
"""
Race pages on the server that the current build no longer makes.

The race-page upload only adds files, so a page for a retired or renamed race
stays on the server after its profile is gone. This compares the server's
/race/ tree with output/ and lists what is left over; with --remove it deletes
exactly those.

    python scripts/stale_race_pages.py            # list only, changes nothing
    python scripts/stale_race_pages.py --remove   # delete the listed leftovers

Run the build first (the generators in CLAUDE.md), so output/ is what the site
should hold. A leftover is removed as the smallest whole directory the build
does not make: /race/<slug>/ when the race is gone, /race/<slug>/<sub>/ when
only a sub-page is. Nothing outside /race/ is ever touched, and every path is
checked against a strict pattern before it reaches the server.
"""

import argparse
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAFE_PART = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def built_documents(output_dir: Path) -> set[str]:
    """Every index.html the race-page upload sends, relative to /race/."""
    docs: set[str] = set()
    for d in sorted(output_dir.iterdir()):
        if d.is_dir() and d.name not in deploy.NON_RACE_OUTPUT_DIRS and (d / "index.html").exists():
            for f in d.rglob("index.html"):
                docs.add(f.relative_to(output_dir).as_posix())
    return docs


def leftover_directories(remote_docs: set[str], built_docs: set[str]) -> list[str]:
    """The smallest whole directories, relative to /race/, that hold only leftovers."""
    built_dirs = {str(Path(doc).parent.as_posix()) for doc in built_docs}
    built_slugs = {doc.split("/", 1)[0] for doc in built_docs}
    out: set[str] = set()
    for doc in sorted(remote_docs - built_docs):
        parts = doc.split("/")[:-1]          # drop index.html
        if not parts or any(not SAFE_PART.match(p) for p in parts):
            raise ValueError(f"refusing an unexpected server path: {doc!r}")
        if parts[0] not in built_slugs:
            out.add(parts[0])                # the whole race is gone
            continue
        # The race is still built: remove the deepest directory the build does not make.
        for depth in range(2, len(parts) + 1):
            candidate = "/".join(parts[:depth])
            if candidate not in built_dirs and not any(b.startswith(candidate + "/") for b in built_dirs):
                out.add(candidate)
                break
        else:
            raise ValueError(f"cannot place a leftover under a built race: {doc!r}")
    return sorted(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--remove", action="store_true", help="delete the leftovers (default: list only)")
    args = parser.parse_args()

    ssh = deploy.get_ssh_credentials()
    if not ssh:
        return 1
    host, user, port = ssh
    remote_race = f"{deploy.get_remote_base()}/race"

    built = built_documents(PROJECT_ROOT / "output")
    if len(built) < 100:
        print(f"  Only {len(built)} built documents in output/: run the build first. Nothing done.")
        return 1

    ok, stdout, err = deploy._ssh_run(
        host, user, port, f"cd {remote_race} && find . -name index.html | sed 's|^\\./||' | sort", timeout=60,
    )
    if not ok:
        print(f"  Could not list the server's race pages: {err}")
        return 1
    remote = {line.strip() for line in stdout.splitlines() if line.strip()}

    missing = sorted(built - remote)
    leftovers = leftover_directories(remote, built)
    print(f"  Server: {len(remote)} documents under /race/. Build: {len(built)}.")
    if missing:
        print(f"  NOT ON SERVER ({len(missing)}): " + ", ".join(missing[:10]))
    if not leftovers:
        print("  No leftover race pages.")
        return 0
    for d in leftovers:
        print(f"  LEFTOVER /race/{d}/")
    # Too many leftovers means the build, not the server, is wrong: never remove in bulk.
    if len(leftovers) > 10:
        print(f"  {len(leftovers)} leftovers is more than a retired race or two. Nothing removed; look first.")
        return 1
    if not args.remove:
        return 0

    for d in leftovers:
        target = f"{remote_race}/{d}"
        ok, _, err = deploy._ssh_run(host, user, port, f"rm -r -- {shlex.quote(target) if not target.startswith('~') else target}")
        if not ok:
            print(f"  Could not remove /race/{d}/: {err}")
            return 1
        print(f"  REMOVED /race/{d}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
