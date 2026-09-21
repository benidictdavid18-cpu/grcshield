"""No source binaries were supplied with the authored sample. Do not invent evidence."""
ATTACHMENT_SEED_POLICY="Metadata references remain missing attachments until the author supplies the actual sample artifact."

def seed_attachments(db):
    # Intentional zero rows: a placeholder file must not count as control evidence.
    return 0
