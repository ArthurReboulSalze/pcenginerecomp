"""Create a new lossless gzip archive of an explicitly offline wire journal.

Never compress a live writer's file. Schema 1 has no close marker; the caller's
offline declaration is required, not inferred from a valid snapshot. The source
is retained unchanged. fsync covers the file, not directory/power-loss durability.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

try:
    from scripts.dev_journal_audit import JournalValidationError, audit_wire_journal, _signature
except ModuleNotFoundError:
    from dev_journal_audit import JournalValidationError, audit_wire_journal, _signature


def archive_wire_journal(source, destination, *, expected_sha256, offline=False,
                         allow_incomplete=False):
    """Audit, copy, fsync, re-audit and exclusively publish one gzip member.

    An externally retained exact source hash and explicit ``offline=True`` are
    mandatory. A source changed between/during reads is refused. Neither this
    declaration nor paired records prove client admission or clean shutdown.
    ``allow_incomplete`` preserves a forensic prefix, never repairs it. The
    final hard-link publication is atomic/no-clobber on filesystems supporting
    it; unsupported publication fails rather than falling back to replacement.
    A crash may leave a private temporary file or a fully written destination.
    No original or pre-existing destination is deleted, renamed or overwritten.
    """
    if offline is not True:
        raise JournalValidationError('explicit offline=True declaration required')
    if expected_sha256 is None:
        raise JournalValidationError('externally retained source SHA256 required')
    source, destination = Path(source), Path(destination)
    original = audit_wire_journal(source, expected_sha256=expected_sha256,
                                  allow_incomplete=allow_incomplete)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('archive destination already exists')
    # No mkdir: the caller chooses and creates the private archive directory.
    descriptor, name = tempfile.mkstemp(prefix='.pce-wire-', suffix='.tmp',
                                      dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as target:
            digest = hashlib.sha256()
            count = 0
            with source.open('rb') as stream:
                start = os.fstat(stream.fileno())
                if not stat.S_ISREG(start.st_mode):
                    raise JournalValidationError('source must remain a regular file')
                with gzip.GzipFile(filename='', mode='wb', compresslevel=6,
                                   fileobj=target, mtime=0) as compressor:
                    while data := stream.read(65536):
                        digest.update(data)
                        count += len(data)
                        compressor.write(data)
                end = os.fstat(stream.fileno())
                if _signature(start) != _signature(end) or _signature(end) != _signature(source.stat()):
                    raise JournalValidationError('source changed during archive copy')
            if digest.hexdigest() != expected_sha256 or count != original['bytes']:
                raise JournalValidationError('source differs from audited snapshot')
            target.flush()
            os.fsync(target.fileno())
        archived = audit_wire_journal(temporary, encoding='gzip',
                                      expected_sha256=expected_sha256,
                                      allow_incomplete=allow_incomplete)
        # A final source audit also rejects ordinary replacement/appending
        # between the copy and archive verification. No filesystem snapshot or
        # locking guarantee is inferred from these read-only stability checks.
        audit_wire_journal(source, expected_sha256=expected_sha256,
                           allow_incomplete=allow_incomplete)
        os.link(temporary, destination)  # Atomic exclusive publication, no replace.
        return dict(schema=1, format='pce-wire-journal-archive-1',
                    offline_declared=True, source_retained=True,
                    source_path=str(source.resolve()), archive_path=str(destination.resolve()),
                    journal_sha256=original['sha256'], journal_bytes=original['bytes'],
                    archive_sha256=archived['storage_sha256'],
                    archive_bytes=archived['storage_bytes'], encoding='gzip',
                    forensic_prefix=archived['forensic_prefix'],
                    record_stream_complete=archived['record_stream_complete'],
                    ending=archived['ending'], records=archived['records'],
                    request_intents=archived['request_intents'],
                    response_frames=archived['response_frames'])
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--sha256', required=True, dest='expected_sha256')
    parser.add_argument('--offline', required=True, action='store_true')
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = archive_wire_journal(args.source, args.destination,
                                      expected_sha256=args.expected_sha256,
                                      offline=args.offline, allow_incomplete=args.allow_incomplete)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, JournalValidationError) as error:
        print('wire journal archive: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
