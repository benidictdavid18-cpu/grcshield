# Backup and restore

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this.

This covers the **platform's own data**, not FinFlow's. The distinction matters: OP-005
is a FinFlow control about FinFlow's backups, tested by TEST-012. Nothing on this page is
evidence that OP-005 operates. This is the tool's own recoverability, which until now was
listed in [SECURITY.md](../SECURITY.md) as an open gap — the uncomfortable kind, because
a system that tracks a backup control had no backup story of its own.

## One artifact, not two

Evidence attachments are stored in the database as `LargeBinary`, not on a filesystem.
So a database archive **is** an attachment archive, and there is one file to take, verify
and restore.

That is a deliberate consequence of where attachments live. The obvious alternative —
dump the database, then separately copy a blob directory — would introduce exactly the
failure a backup exists to prevent: two artifacts taken at different moments, restored
together, disagreeing about which attachments existed.

## Logical, not physical

The archive is a gzipped JSON document built from the model metadata, not a `pg_dump` or
a copied SQLite file. That costs speed and size on a large database, which this is not.
It buys three things this project actually needs:

- **It restores across dialects.** A PostgreSQL deployment can be rehearsed against
  SQLite, which is how the restore is exercised in the test suite.
- **It is readable.** An auditor can see what was retained without the application.
- **It needs no database tooling** wherever the restore happens.

## Commands

```bash
python scripts/backup.py create --dir backups
```

```bash
python scripts/backup.py verify backups/grcshield-20261002-091500.grcshield
```

```bash
python scripts/backup.py restore backups/grcshield-20261002-091500.grcshield --replace
```

```bash
python scripts/backup.py prune --dir backups --keep-days 90
```

`create` writes `grcshield-YYYYMMDD-HHMMSS.grcshield` and prints the manifest and digest.
`verify` reads an archive and checks it against its own digest without touching a
database. `prune` applies the retention window and **never removes the most recent
archive**, whatever its age — an empty backup directory is a worse outcome than one
stale file.

## What is refused

A restore is the single operation here most likely to destroy the thing it protects, so
three cases are refused rather than warned about:

| Refusal | Why |
| --- | --- |
| The body does not match its recorded digest | The archive was truncated or altered. Restoring it would load data nobody can vouch for. |
| The archive's migration revision differs from the database's | Restoring yesterday's columns into today's schema loses the difference silently. Bring the database to the archive's revision first. |
| The target already holds data and `--replace` was not passed | Overwriting a live database is a decision, not a default. |

Each raises a typed error — `ArchiveCorrupt`, `SchemaMismatch`, `TargetNotEmpty` — and
the CLI reports it as `REFUSED:` with a non-zero exit, so a failed backup job is a failed
job rather than a silent one.

## Access

The archive holds every record in the system, including evidence attachment bytes and
bcrypt password hashes. It carries the same sensitivity as the database and belongs under
the same access control. `scripts/backup.py` reads `DATABASE_URL` from the environment
and holds no credentials of its own.

## What is tested

`backend/tests/test_backup.py` exercises the round trip and all three refusals:

- an archive of the seeded database restores into an empty one with every table's row
  count intact, and RISK-004 comes back at inherent 4 × 5;
- binary and date columns survive encoding, which is the payload most likely to be
  quietly corrupted;
- a tampered body, a file that is not an archive, a schema mismatch and a non-empty
  target are each refused.

An untested backup is a belief. These run with the rest of the suite, so the claim on
this page fails the build when it stops being true.

## What this is not

- **Not point-in-time recovery.** The archive is a snapshot. There is no write-ahead log
  shipping and no restore to an arbitrary moment between archives.
- **Not offsite.** Where archives are stored, and whether that location is itself backed
  up, is a deployment decision this repository does not make.
- **Not a schedule.** Nothing runs `create` on a timer. In a real deployment that is a
  cron entry or a platform job, with the retention window beside it.
