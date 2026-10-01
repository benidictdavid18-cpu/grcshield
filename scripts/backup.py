"""Create, verify, restore and prune GRCShield archives.

    python scripts/backup.py create  --dir backups
    python scripts/backup.py verify  backups/grcshield-20261002-091500.grcshield
    python scripts/backup.py restore backups/grcshield-20261002-091500.grcshield --replace
    python scripts/backup.py prune   --dir backups --keep-days 90

The rules live in ``app.services.backup``; this file is how an operator reaches them.
It adds the two things the service deliberately leaves out, because they are
operational rather than data concerns: where archives are written, and how long they
are kept.

``restore`` refuses a non-empty database unless ``--replace`` is passed. That is not
caution for its own sake -- a restore into a live database is the single operation in
this repository most likely to destroy the thing it exists to protect.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.services import backup  # noqa: E402

SUFFIX = ".grcshield"


def cmd_create(args: argparse.Namespace) -> int:
    now = dt.datetime.now(dt.UTC)
    directory = Path(args.dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"grcshield-{now.strftime('%Y%m%d-%H%M%S')}{SUFFIX}"

    with Session(engine) as db:
        archive = backup.create(db, now=now)
    path.write_bytes(archive)

    manifest = backup.inspect(archive)
    print(f"Wrote {path} ({path.stat().st_size / 1024:.1f} KiB)")
    print(f"  {manifest.summary}")
    print(f"  sha256 {manifest.digest}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        manifest = backup.inspect(Path(args.archive).read_bytes())
    except backup.BackupError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"{args.archive} is readable and intact.")
    print(f"  {manifest.summary}")
    for name, count in sorted(manifest.table_counts.items()):
        if count:
            print(f"    {count:>6}  {name}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    archive = Path(args.archive).read_bytes()
    try:
        with Session(engine) as db:
            manifest = backup.restore(db, archive, replace=args.replace)
    except backup.BackupError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"Restored {manifest.summary}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    """Retention. Keeps the most recent archive whatever its age.

    An empty backup directory is a worse outcome than one stale archive, so the newest
    is never removed even when every archive is past the retention window.
    """
    cutoff = dt.datetime.now().timestamp() - args.keep_days * 86400
    archives = sorted(
        Path(args.dir).glob(f"*{SUFFIX}"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not archives:
        print(f"No archives in {args.dir}.")
        return 0

    removed = 0
    for path in archives[1:]:
        if path.stat().st_mtime < cutoff:
            path.unlink()
            print(f"Removed {path.name}")
            removed += 1
    print(f"{removed} removed, {len(archives) - removed} kept (newest always retained).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="write a new archive")
    create.add_argument("--dir", default="backups")
    create.set_defaults(func=cmd_create)

    verify = sub.add_parser("verify", help="check an archive without a database")
    verify.add_argument("archive")
    verify.set_defaults(func=cmd_verify)

    restore = sub.add_parser("restore", help="load an archive into the configured database")
    restore.add_argument("archive")
    restore.add_argument(
        "--replace", action="store_true", help="overwrite a database that already holds data"
    )
    restore.set_defaults(func=cmd_restore)

    prune = sub.add_parser("prune", help="apply a retention window to a backup directory")
    prune.add_argument("--dir", default="backups")
    prune.add_argument("--keep-days", type=int, default=90)
    prune.set_defaults(func=cmd_prune)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
