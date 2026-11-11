"""Export the remaining procurement-selection groups without choosing parts.

The 2026-11-10 worksheet is the requirements source; the freshly exported
canonical BOMs and XML netlists decide which references are still pending.
Only docs/parts_to_complete_2026-11-11 is written.
"""
from collections import Counter
from pathlib import Path
import csv
import hashlib
import json
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'docs/parts_to_complete_2026-11-10/selection_pending.csv'
OUTPUT = REPO / 'docs/parts_to_complete_2026-11-11'
BOARDS = {
    'controller': REPO / 'controller/hardware/g431_core',
    'inverter': REPO / 'inverter/hardware',
}
REMOVED = {
    'controller': {'C304', 'C306', 'C307', 'C308'},
    'inverter': {'C4', 'C5', 'C9', 'C12', 'C24', 'C26', 'C28', 'C30',
                 'C32', 'C34', 'C36', 'C37', 'C38', 'C39', 'C51', 'C52', 'C53'},
}
EXPECTED = {
    'controller': {'groups': 13, 'references': 26, 'fitted': 23, 'DNP': 3},
    'inverter': {'groups': 52, 'references': 207, 'fitted': 197, 'DNP': 10},
}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pending(row):
    return (not row['Reference'].startswith('TP')
            and row['MPN'] != 'PCB solder holes / wire assembly'
            and (not row['MPN'] or 'TBD' in row['MPN'].upper()))


def load_board(role, directory):
    bom_path = directory / 'bom/bom.csv'
    pending_path = directory / 'bom/selection_pending.csv'
    xml_path = directory / 'review' / (role + '.net.xml')
    _, rows = read_csv(bom_path)
    _, supplied_pending = read_csv(pending_path)
    by_ref = {row['Reference']: row for row in rows}
    assert len(by_ref) == len(rows), (role, 'duplicate canonical BOM reference')
    expected_pending = {ref: row for ref, row in by_ref.items() if pending(row)}
    supplied_by_ref = {row['Reference']: row for row in supplied_pending}
    assert len(supplied_by_ref) == len(supplied_pending)
    assert supplied_by_ref == expected_pending, (role, 'canonical pending CSV is stale')

    root = ET.parse(xml_path).getroot()
    parts = {part.get('ref'): part for part in root.findall('./components/comp')}
    assert set(parts) == set(by_ref), (role, 'BOM/XML reference set differs')
    for ref, part in parts.items():
        fields = {field.get('name'): field.text or ''
                  for field in part.findall('./fields/field')}
        expected = {key: fields.get(key, '') for key in by_ref[ref]}
        expected.update(Reference=ref, Value=part.findtext('value') or '', Quantity='1',
                        DNP='yes' if part.find("property[@name='dnp']") is not None else 'no',
                        Sheet=part.find('sheetpath').get('names'),
                        Footprint=part.findtext('footprint') or '')
        assert by_ref[ref] == expected, (role, ref, 'canonical BOM is stale',
            {key: (by_ref[ref][key], expected[key]) for key in expected
             if by_ref[ref][key] != expected[key]})
    for ref in REMOVED[role]:
        row = by_ref[ref]
        assert row['Supplier_PN'] == 'C14663' and row['MPN'] == 'CC0603KRX7R9BB104'
        assert row['Verification'] == 'reviewed', (role, ref, 'new part not reviewed')
        assert ref not in expected_pending
    return by_ref, expected_pending, [bom_path, pending_path, xml_path]


def main():
    columns, original = read_csv(SOURCE)
    output = []
    source_paths = [SOURCE]
    all_pending, all_parts, original_refs = {}, {}, {}
    for role, directory in BOARDS.items():
        all_parts[role], all_pending[role], paths = load_board(role, directory)
        source_paths.extend(paths)
        original_refs[role] = set()

    removed_groups = []
    for row in original:
        role = row['板卡']
        refs = row['位号'].split()
        assert len(refs) == len(set(refs)), (row['编号'], 'duplicate reference')
        assert not original_refs[role].intersection(refs), (row['编号'], 'overlapping group')
        original_refs[role].update(refs)
        remaining = set(refs).intersection(all_pending[role])
        if not remaining:
            assert set(refs) <= REMOVED[role], (row['编号'], 'unexpected removed group')
            removed_groups.append({'original_group': row['编号'], 'board': role,
                                   'references': refs, 'MPN': 'CC0603KRX7R9BB104',
                                   'Supplier_PN': 'C14663'})
            continue
        # This migration resolves two whole groups. Never silently truncate
        # per-reference requirements if a later selection splits a group.
        assert remaining == set(refs), (row['编号'], 'partially resolved group needs review')
        assert not set(refs).intersection(REMOVED[role])
        members = [all_pending[role][ref] for ref in refs]
        assert {item['Footprint'] for item in members} == {row['现用封装']}
        assert {item['Value'] for item in members} == {row['现有数值']}
        dnp = [item['Reference'] for item in members if item['DNP'] == 'yes']
        assert int(row['DNP数']) == len(dnp)
        assert int(row['装配数']) == len(refs) - len(dnp)
        assert set(row['DNP位号'].split()) == set(dnp)
        output.append(dict(row))  # Retain all requirements/candidates verbatim.

    statistics = {}
    for role in BOARDS:
        assert original_refs[role] - set(all_pending[role]) == REMOVED[role]
        rows = [row for row in output if row['板卡'] == role]
        covered = [ref for row in rows for ref in row['位号'].split()]
        assert len(covered) == len(set(covered))
        assert set(covered) == set(all_pending[role]), (role, 'pending coverage mismatch')
        statistics[role] = {
            'groups': len(rows), 'references': len(covered),
            'fitted': sum(int(row['装配数']) for row in rows),
            'DNP': sum(int(row['DNP数']) for row in rows),
        }
        assert statistics[role] == EXPECTED[role], (role, statistics[role])
    totals = {key: sum(row[key] for row in statistics.values())
              for key in ('groups', 'references', 'fitted', 'DNP')}
    assert totals == {'groups': 65, 'references': 233, 'fitted': 220, 'DNP': 13}
    assert {row['original_group'] for row in removed_groups} == {'S04', 'S26'}
    summary = {
        'date': '2026-11-11', 'revision': 'E-shared-library-draft',
        'scope': 'Remaining exact procurement model selection; no new model selected.',
        'boards': statistics, 'total': totals,
        'categories': dict(Counter(row['类别'] for row in output)),
        'removed_reviewed_groups': removed_groups,
        'requirements_preserved': 'All surviving worksheet rows and columns are unchanged.',
        'source_sha256': {str(path.relative_to(REPO)).replace('\\', '/'): digest(path)
                          for path in source_paths},
    }
    readme = '''# 待补采购型号清单（2026-11-11）

`selection_pending.csv` 是当前两块板的采购选型工作表，共 65 组、233 个位号：220 个装配位号、13 个 DNP 位号。controller 为 13 组 / 26 位号，inverter 为 52 组 / 207 位号。

表格沿用 2026-11-10 清单的列、分组编号、额定电压、公差、厂家要求、逐位号说明和已有候选记录。原 S04、S26 的 21 个 100 nF / 0603 位号已采用共享库 reviewed 物料 CC0603KRX7R9BB104 / C14663，因此剔除；其余 65 行保持原文，编号留空缺便于追溯。

填写“补充完整型号”“补充立创编号”“补充采购链接”；采购链接使用国内立创商城。已有候选及候选链接仅保留历史线索，不代表已选定或可直接下单。

这些分组只是选型起点。每个型号须满足组内所有逐位号要求；如有效容量、脉冲功率、精度或装配状态要求不同，应拆组复核。DNP 表示当前不装配，仍保留在工作表中；不能把它计入本版实装采购数量。普通电阻电容仍按表内国巨要求；未在这里新选任何型号。

从仓库根目录运行 `python tools/export_pending_parts.py` 可重新生成本目录。工具先核对 canonical BOM、待选 BOM 与最新 XML 完全一致，再核对分组覆盖和统计；不修改原理图、共享库或原 BOM。`summary.json` 记录输入 SHA-256、移除位号和分板统计。
'''
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / 'selection_pending.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(output)
    (OUTPUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUTPUT / 'README.md').write_text(readme, encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'boards': statistics, 'total': totals,
                      'output': str(OUTPUT.relative_to(REPO)).replace('\\', '/')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
