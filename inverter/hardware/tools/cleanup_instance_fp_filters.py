"""Remove only instance ki_fp_filters fields identical to embedded library defaults.

Default is read-only.  --write removes the exact property text spans and records
the file hashes / affected units in review/symbol_filter_cleanup.json.  Embedded
lib_symbols bytes and every other native S-expression must remain unchanged.
"""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json
import sexpdata as sx

BASE = Path(__file__).resolve().parents[1]
FIELD = 'ki_fp_filters'
REASON = ('KiCad 10 reserves ki_fp_filters for library footprint selection. '
          'Redundantly copying it to instance user fields causes PCB parity '
          'warnings because pcbnew drops the reserved name on PCB load. '
          'The embedded library filter is retained unchanged.')


def children(data, tag):
    return [item for item in data if isinstance(item, list) and item and str(item[0]) == tag]


def child(data, tag):
    return next(iter(children(data, tag)), None)


def properties(data):
    return {item[1]: item[2] for item in children(data, 'property')}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def direct_list_spans(text):
    """Yield exact direct-child list offsets, respecting quoted escapes/comments."""
    depth = 0
    quoted = escaped = comment = False
    start = None
    for index, char in enumerate(text):
        if comment:
            if char in '\r\n':
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == ';':
            comment = True
        elif char == '"':
            quoted = True
        elif char == '(':
            if depth == 1:
                start = index
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 1 and start is not None:
                yield start, index + 1
                start = None
    assert depth == 0 and not quoted, 'Invalid/unbalanced native S-expression'


def plan(path):
    original = path.read_bytes()
    text = original.decode('utf-8-sig')
    source = sx.loads(text)
    embedded = child(source, 'lib_symbols')
    libs = {item[1]: item for item in children(embedded, 'symbol')}
    target = copy.deepcopy(source)
    removals, records = [], []
    library_text = None
    for start, end in direct_list_spans(text):
        fragment = text[start:end]
        if fragment.startswith('(lib_symbols'):
            library_text = fragment
        if not fragment.startswith('(symbol '):
            continue
        instance = sx.loads(fragment)
        fields = properties(instance)
        if FIELD not in fields:
            continue
        lib_id = child(instance, 'lib_id')[1]
        default = properties(libs[lib_id]).get(FIELD)
        assert default is not None and fields[FIELD] == default, (
            path.name, fields['Reference'], 'refuse to remove non-default filter', fields[FIELD], default)
        candidates = []
        for inner_start, inner_end in direct_list_spans(fragment):
            item = sx.loads(fragment[inner_start:inner_end])
            if isinstance(item, list) and str(item[0]) == 'property' and item[1] == FIELD:
                candidates.append((start+inner_start, start+inner_end))
        assert len(candidates) == 1, (path.name, fields['Reference'], 'duplicate filter fields')
        removals.extend(candidates)
        records.append({'sheet_file': path.name, 'reference': fields['Reference'],
                        'unit': child(instance, 'unit')[1], 'lib_id': lib_id,
                        'removed_instance_value': fields[FIELD], 'retained_library_value': default})
    for instance in children(target, 'symbol'):
        for item in children(instance, 'property'):
            if item[1] == FIELD:
                instance.remove(item)
    new_text = text
    for start, end in sorted(removals, reverse=True):
        new_text = new_text[:start] + new_text[end:]
    assert sx.loads(new_text) == target, (path.name, 'change beyond redundant property removal')
    assert library_text is None or library_text in new_text, (path.name, 'embedded library bytes changed')
    prefix = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
    updated = prefix + new_text.encode('utf-8')
    return original, updated, records, digest((library_text or '').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    # Preflight every page before modifying any file.
    plans = [(path, *plan(path)) for path in sorted(BASE.glob('*.kicad_sch'))]
    records = [entry for _, _, _, entries, _ in plans for entry in entries]
    report = {'field': FIELD, 'reason': REASON,
              'removed_instance_unit_fields': len(records),
              'affected_physical_references': len({entry['reference'] for entry in records}),
              'counts_by_sheet': dict(Counter(entry['sheet_file'] for entry in records)),
              'embedded_library_filters_preserved': True,
              'all_other_native_semantics_preserved': True,
              'files': [{'path': path.name, 'before_sha256': digest(original),
                         'after_sha256': digest(updated), 'embedded_lib_symbols_sha256': library_hash}
                        for path, original, updated, entries, library_hash in plans if entries],
              'removed_fields': records}
    if args.write:
        for path, original, updated, entries, _ in plans:
            if entries:
                path.write_bytes(updated)
        output = BASE/'review/symbol_filter_cleanup.json'
        if records or not output.exists():
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ['files', 'removed_fields']}, ensure_ascii=False))
    print('Applied.' if args.write else 'Dry run only; use --write to apply.')


if __name__ == '__main__':
    main()
