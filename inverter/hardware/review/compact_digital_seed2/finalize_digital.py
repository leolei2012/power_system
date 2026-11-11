"""Read-only independent summary and scope proof for the digital delta."""
import collections
import hashlib
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(B / 'tools'))
import compact_stitch_signals as s

base = B / 'inverter.kicad_pcb'
candidate = B / 'review/compact_finish_digital_precision.work/inverter.kicad_pcb'
patch_path = B / 'review/compact_finish_digital.json'
stats = json.loads((B / 'review/compact_digital_seed2/source_scope_stats.json').read_text())
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(base) == stats['source_sha'] == '4d4f0c2ae1d5177ebf351e92cd70ae8483fde624233a5b98dc958461cede13fb'
assert sha(base.with_suffix('.kicad_pro')) == '6deb935ec5d0c9eb3f1ff1d00b76b9d00cdf18db3bc1566d2adb7fbcafd7554b'
old = s.p.LoadBoard(str(base))
new = s.p.LoadBoard(str(candidate))
bc = s.native_components(old)
ac = s.native_components(new)
nets = set(stats['nets'])
before = sum(max(bc.get(n, 0) - 1, 0) for n in nets)
after = sum(max(ac.get(n, 0) - 1, 0) for n in nets)
global_before = old.GetConnectivity().GetUnconnectedCount(False)
global_after = new.GetConnectivity().GetUnconnectedCount(False)
regressions = {n: [bc.get(n, 0), count] for n, count in ac.items() if count > bc.get(n, 0)}
outside_scope_changes = {n: [bc.get(n, 0), ac.get(n, 0)] for n in set(bc) | set(ac) if n not in nets and bc.get(n, 0) != ac.get(n, 0)}
assert not regressions and not outside_scope_changes
assert before == 88 and global_before == 215
assert before - after == global_before - global_after
new_geometry = s.original_geometry(new)
original_changes = [uid for uid, v in s.original_geometry(old).items() if new_geometry.get(uid) != v]
assert not original_changes
drc_file = candidate.parent / 'final_drc.json'
fixed_file = candidate.parent / 'final_fixed.json'
drc = json.loads(drc_file.read_text())
fixed = json.loads(fixed_file.read_text())
errors = [v for v in drc.get('violations', []) if v.get('severity') == 'error']
assert not errors and not fixed['issues']
patch = json.loads(patch_path.read_text())
assert patch['source_sha'] == sha(base)
assert not patch['ripup_uuids'] and not patch['placements']
assert {q['net'] for q in patch['paths'] + patch['vias']} <= nets
summary = {
    'source_sha': sha(base),
    'candidate_sha256': sha(candidate),
    'scope': 'Owned 76 exact digital net names from original 88-gap DRC scope',
    'before_scope_gaps': before, 'after_scope_gaps': after,
    'digital_gaps_closed': before - after,
    'before_global_native_gaps': global_before, 'after_global_native_gaps': global_after,
    'drc_listed_airwires': len(drc.get('unconnected_items', [])),
    'drc_electrical_errors': len(errors),
    'drc_nonconnection_violation_severities': dict(collections.Counter(v.get('severity') for v in drc.get('violations', []))),
    'drc_nonconnection_violation_types': dict(collections.Counter(v.get('type') for v in drc.get('violations', []))),
    'fixed_kelvin_pass': not fixed['issues'],
    'fixed_summary': fixed['summary'],
    'original_geometry_changes': original_changes,
    'outside_scope_component_changes': outside_scope_changes,
    'component_regressions': regressions,
    'project_identical': base.with_suffix('.kicad_pro').read_bytes() == candidate.with_suffix('.kicad_pro').read_bytes(),
    'ripup_count': len(patch['ripup_uuids']), 'added_segments': len(patch['paths']), 'added_vias': len(patch['vias']),
    'drc_report': str(drc_file.relative_to(B)), 'fixed_report': str(fixed_file.relative_to(B)),
    'remaining_scope_net_gaps': {n: ac.get(n, 0) - 1 for n in sorted(nets) if ac.get(n, 0) > 1},
    'improved_nets': {n: {'before': bc.get(n, 0) - 1, 'after': ac.get(n, 0) - 1} for n in sorted(nets) if bc.get(n, 0) != ac.get(n, 0)},
    'source_unchanged': sha(base) == stats['source_sha'],
}
assert summary['project_identical']
out = candidate.parent / 'final_scope_verification.json'
out.write_text(json.dumps(summary, indent=2) + '\n')
patch['validation'] = summary
patch['notes'] = ['Additive digital-only delta against frozen source. No ripup, placement, footprint, pad-net, rule, or original geometry changes.', '20 owned gaps closed. Remaining 68 digital gaps are deliberately unresolved after native-exact and conservative raster passes; this is not a completely routed board.', 'DRC0 electrical violations; 195 airwires and 11 track_dangling warnings remain across all scopes.']
patch_path.write_text(json.dumps(patch, indent=2) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k not in ('remaining_scope_net_gaps', 'improved_nets')}, indent=2))
