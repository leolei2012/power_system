"""Explicit private/owning-project opt-in for .125 mm ordinary signals.

Run with KiCad Python. This changes only the same-name project for --board;
it never saves a PCB or schematic. Use a private PCB copy for experiments.
Example: python compact_signal_rules.py --board PRIVATE/inverter.kicad_pcb \
  --net SPI_A_SCK --net MCU_ENABLE --out PRIVATE/fine_rules.json
Power, reference, source, shunt and intermediate voltage-divider nets cannot
be assigned. Existing Default/Gate/Auxiliary/HV classes and patterns remain.
"""
from __future__ import annotations
import argparse
import copy
import fnmatch
import hashlib
import json
import re
from pathlib import Path

FINE_WIDTH = .125
VIA_DIAMETER = .5
VIA_DRILL = .2
MIN_CLEARANCE = .15
GLOBAL_DIGITAL = re.compile(
    r'(?:AUX_FLT_N|BOOT0|BRAKE_IN|BUS_OV_OK|CAN_(?:TX|RX)|DRIVE_PERMIT|'
    r'DRV_(?:PG_LOGIC|UV_OK)|ENABLE_IN|FAULT_N|HSE_(?:IN|OUT)|LOGIC_POWER_OK|'
    r'ENC_[AB]_[ABZ]|LED_(?:AUX|COMM|FAULT|RUN)|MCU_(?:BRAKE|ENABLE|PWM_[UVW][HL])|'
    r'OC_[UVW]_(?:HIGH|LOW)_OK|PWM_[UVW][HL]_IN|SPI_[AB]_(?:SCK|MISO|MOSI|CS)|'
    r'SWCLK|SWDIO|UART_(?:TX|RX)|[UVW]_[HL]IN)')
ADC_FINAL = re.compile(r'ADC_(?:I_[UVW]|V_(?:DC|[UVW])|TEMP_NTC)')
LOCAL_DIGITAL = re.compile(
    r'(?:/Hardware latch/(?:ENABLE_N|FAULT_(?:ACTIVE|BASE|LATCH)|HEALTH_(?:ALL|CHAIN_[1-9]|UNLATCHED)|NO_LATCH|RESET_(?:CLK|REQUEST))|'
    r'/Debug and communication/(?:CAN_(?:[HL]|[TR]X_PHY)|LED_AN_[0-4]|SWCLK_PORT|SWDIO_PORT|UART_[TR]X_PORT)|'
    r'/Encoders and SPI/(?:ENC_[AB]_[ABZ]_PORT|SPI_[AB]_(?:CS|MISO|MOSI|SCK)_PORT)|'
    r'/Logic and sensors/SENSOR_PWR_FLT_N)')

def eligible(name):
    """An explicit known-circuit allowlist, never a broad power-net denylist."""
    return bool(GLOBAL_DIGITAL.fullmatch(name) or ADC_FINAL.fullmatch(name) or LOCAL_DIGITAL.fullmatch(name))

def assigned_classes(name, project):
    ns = project.get('net_settings', {})
    result = set()
    value = ns.get('netclass_assignments', {}).get(name, [])
    result.update([value] if isinstance(value, str) else value)
    for item in ns.get('netclass_patterns', []):
        if fnmatch.fnmatchcase(name, item['pattern']):
            result.add(item['netclass'])
    return result or {'Default'}

def fine_assigned(name, project):
    return eligible(name) and assigned_classes(name, project) == {'FineSignal'}

def clearance_for(name, project):
    classes = {c['name']: c for c in project.get('net_settings', {}).get('classes', [])}
    return max([MIN_CLEARANCE] + [classes.get(n, {}).get('clearance', MIN_CLEARANCE) for n in assigned_classes(name, project)])

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def configure(board, names, out):
    import pcbnew as p
    board = Path(board).resolve()
    project_file = board.with_suffix('.kicad_pro')
    project = json.loads(project_file.read_text(encoding='utf-8'))
    before = copy.deepcopy(project)
    pcb_sha = sha(board)
    actual = {n.GetNetname() for n in p.LoadBoard(str(board)).GetNetsByNetcode().values()}
    if not names:
        raise ValueError('At least one explicit --net is required')
    for name in names:
        if name not in actual or not eligible(name):
            raise ValueError('Unknown or forbidden fine signal: ' + name)
        current = assigned_classes(name, project)
        if current - {'Default', 'FineSignal'}:
            raise ValueError('Higher-clearance/class net cannot be overridden: ' + name + ': ' + repr(current))
    ns = project['net_settings']
    default = next(c for c in ns['classes'] if c['name'] == 'Default')
    if (default['track_width'], default['via_diameter'], default['via_drill']) != (.15, .6, .3):
        raise ValueError('Expected unchanged Default .15/.6/.3 preferences')
    fine = copy.deepcopy(default)
    fine.update(name='FineSignal', priority=1, clearance=.15, track_width=.125, via_diameter=.5, via_drill=.2)
    old_fine = [c for c in ns['classes'] if c['name'] == 'FineSignal']
    if old_fine and old_fine != [fine]:
        raise ValueError('Existing FineSignal definition differs; refusing to replace it')
    if not old_fine:
        ns['classes'].append(fine)
    for name in sorted(set(names)):
        item = {'netclass': 'FineSignal', 'pattern': name}
        if item not in ns['netclass_patterns']:
            ns['netclass_patterns'].append(item)
    rules = project['board']['design_settings']['rules']
    changed = {}
    for key, value in {'min_track_width': .125, 'min_via_diameter': .5,
                       'min_through_hole_diameter': .2, 'min_via_annular_width': .15,
                       'min_clearance': max(.15, rules.get('min_clearance', 0))}.items():
        if rules.get(key) != value:
            changed[key] = {'before': rules.get(key), 'after': value}
        rules[key] = value
    for name in names:
        if not fine_assigned(name, project):
            raise ValueError('Conflicting netclass remains: ' + name)
    for c in before['net_settings']['classes']:
        assert c in project['net_settings']['classes'], 'Original netclass changed'
    assert before['net_settings']['netclass_assignments'] == ns['netclass_assignments']
    assert all(q in ns['netclass_patterns'] for q in before['net_settings']['netclass_patterns'])
    report = {'board': str(board), 'board_sha256': pcb_sha,
              'project': str(project_file), 'before_project_sha256': sha(project_file),
              'selected_exact_nets': sorted(set(names)), 'changed_global_minima': changed,
              'fine_class': fine, 'preserved_original_classes': [c['name'] for c in before['net_settings']['classes']],
              'policy': 'Only .125 trace/.5-.2 throughvia minima and explicit FineSignal opt-in; real minimum clearance .15, annular .15; all original class definitions, patterns, severities, hole/edge rules, routing preferences and all PCB bytes preserved.'}
    project_file.write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8')
    assert sha(board) == pcb_sha
    report['after_project_sha256'] = sha(project_file)
    out = Path(out) if out else board.parent / 'fine_signal_rules.json'
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Configured', len(set(names)), 'exact fine nets; PCB unchanged:', board)
    print('Report:', out)
    return report

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, required=True)
    ap.add_argument('--net', action='append', default=[], help='Repeat exact allowed digital/final-ADC net name; no glob')
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    configure(args.board, args.net, args.out)

if __name__ == '__main__':
    main()
