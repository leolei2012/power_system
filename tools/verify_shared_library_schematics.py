"""Verify the current two schematics after adopting reviewed shared components.

Read-only circuit checks, using the pre-change Rev E XML as the electrical
baseline. Writes reports only; never regenerates or changes schematic sources.
"""
from pathlib import Path
from collections import defaultdict, Counter
import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET

import sexpdata as sx

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / 'controller/hardware/g431_core'
BASE = REPO / 'inverter/hardware'
LIB = REPO.parent / 'kicad_library'
STD_FP = Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
DATE = '2026-11-11'


def children(node, tag):
    return [x for x in node if isinstance(x, list) and x and str(x[0]) == tag]


def child(node, tag):
    return next(iter(children(node, tag)), None)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_netlist(path):
    root = ET.parse(path).getroot()
    parts = {x.get('ref'): x for x in root.findall('./components/comp')}
    nets, pins = {}, {}
    for net in root.findall('./nets/net'):
        nodes = frozenset((n.get('ref'), n.get('pin')) for n in net.findall('node') if n.get('ref') in parts)
        if nodes:
            nets[net.get('code')] = nodes
        for node in nodes:
            assert node not in pins, ('duplicate netlist pin', node)
            pins[node] = net.get('name')
    return {'parts': parts, 'nets': nets, 'pins': pins, 'path': path}


def fields(part):
    return {x.get('name'): x.text or '' for x in part.findall('./fields/field')}


def short_net(board, ref, pin):
    return board['pins'][(ref, str(pin))].rsplit('/', 1)[-1]


def is_dnp(part):
    return part.find("property[@name='dnp']") is not None


def board_checks(role, before, after, shared):
    assert set(before['parts']) == set(after['parts']), (role, 'reference set changed')
    assert set(before['pins']) == set(after['pins']), (role, 'physical pin set changed')
    old_partitions, new_partitions = set(before['nets'].values()), set(after['nets'].values())
    assert old_partitions == new_partitions, (role, 'electrical connectivity changed',
        [sorted(x) for x in old_partitions-new_partitions], [sorted(x) for x in new_partitions-old_partitions])
    checks = []
    known, unknown = [], []
    board_dir = CORE if role == 'controller' else BASE
    for ref, part in after['parts'].items():
        previous = before['parts'][ref]
        assert is_dnp(previous) == is_dnp(part), (role, ref, 'DNP changed')
        f = fields(part)
        code = f.get('Supplier_PN', '')
        footprint = part.findtext('footprint') or ''
        assert footprint, (role, ref, 'missing footprint')
        nickname, fpname = footprint.split(':', 1)
        if nickname == 'MyFootprints':
            fpfile = LIB / 'footprints/MyFootprints.pretty' / (fpname + '.kicad_mod')
        elif (board_dir / (nickname + '.pretty')).is_dir():
            fpfile = board_dir / (nickname + '.pretty') / (fpname + '.kicad_mod')
        else:
            fpfile = STD_FP / (nickname + '.pretty') / (fpname + '.kicad_mod')
        assert fpfile.exists(), (role, ref, fpfile)
        pads = {str(p[1]) for p in children(sx.loads(fpfile.read_text(encoding='utf-8-sig')), 'pad') if str(p[1])}
        pin_numbers = {pin for rr, pin in after['pins'] if rr == ref}
        assert pin_numbers <= pads, (role, ref, 'pins without pads', pin_numbers-pads)
        if code:
            assert code in shared, (role, ref, 'C number not built', code)
            item = shared[code]
            assert item['Verification'] in ('reviewed', 'prototype_verified'), (code, 'unreviewed')
            source = part.find('libsource')
            assert source is not None
            assert source.get('lib') + ':' + source.get('part') == item['Symbol'], (role, ref, 'symbol mismatch')
            assert footprint == item['Footprint'], (role, ref, 'footprint mismatch')
            assert f.get('MPN') == item['MPN'], (role, ref, 'MPN mismatch', f.get('MPN'), item['MPN'])
            for key in ('Manufacturer', 'Supplier'):
                assert f.get(key) == item[key], (role, ref, key + ' mismatch')
            if code == 'C412739':
                fpdata = sx.loads(fpfile.read_text(encoding='utf-8-sig'))
                copper_pads = [str(p[1]) for p in children(fpdata, 'pad')
                               if str(p[1]) and any(str(layer).endswith('.Cu') or str(layer) == '*.Cu'
                                                   for layer in child(p, 'layers')[1:])]
                assert Counter(copper_pads) == Counter(list('12345678') + ['5']), (role, ref, 'MOS pad numbering')
            assert re.match(r'^https://(?:item|so)\.szlcsc\.com/', f.get('Purchase_URL', '')), (role, ref, 'purchase URL must be domestic')
            known.append(ref)
        elif not ref.startswith('TP') and f.get('MPN', '').upper() in ('', 'TBD'):
            unknown.append(ref)
        if previous.findtext('footprint') != footprint or previous.findtext('value') != part.findtext('value') or fields(previous).get('MPN') != f.get('MPN'):
            assert code in shared, (role,ref,'unapproved change to a pending component')
            checks.append({'ref':ref,'before_value':previous.findtext('value'),'after_value':part.findtext('value'),
                'before_footprint':previous.findtext('footprint'),'after_footprint':footprint,
                'C_number':code})
    return {'components':len(after['parts']),'DNP':sum(is_dnp(x) for x in after['parts'].values()),
            'physical_pin_nodes':len(after['pins']),'unchanged_net_partitions':len(new_partitions),
            'shared_reviewed_references':known,'selection_pending_references':unknown,
            'approved_metadata_changes':checks,'netlist_sha256':sha(after['path'])}


def functional_checks(core, base, contract):
    c = lambda ref, pin: short_net(core, ref, pin)
    b = lambda ref, pin: short_net(base, ref, pin)
    contact_checks = []
    for ref in ('J101','J102'):
        for pin, expected in contract[ref].items():
            cw = contract['supply_alias'][expected]['controller'] if expected in contract['supply_alias'] else expected
            bw = contract['supply_alias'][expected]['inverter'] if expected in contract['supply_alias'] else expected
            assert c(ref,pin) == cw, ('core header',ref,pin,c(ref,pin),cw)
            if expected in contract['base_unassigned_ports']:
                assert b(ref,pin).startswith('unconnected-'), ('base unused',ref,pin)
            else:
                assert b(ref,pin) == bw, ('base header',ref,pin,b(ref,pin),bw)
            contact_checks.append({'header':ref,'pin':int(pin),'core_net':c(ref,pin),'base_net':b(ref,pin)})
    assert len(contact_checks) == 64
    gpio = {str(x['mcu_pad']):x['net'] for rows in contract['pins'].values() for x in rows if x['kind']=='mcu_signal'}
    assert len(gpio) == len(set(gpio.values())) == 52
    for pad, net in gpio.items():
        assert c('U30',pad) == net, ('MCU pad',pad,net)
    assert not any(c('U30',pad).startswith('unconnected-') for pad in range(1,65))
    assert [c('SW2',p) for p in (1,2)] == ['NRST','GND']
    assert c('SW3',1) == '+3V3_MCU' and c('SW3',2) == c('R401',1)
    assert c('R401',2) == 'PB8_BOOT0'
    assert [c('R122',p) for p in (1,2)] == ['PB8_BOOT0','GND']
    assert [c('U105',p) for p in (1,2,3,4,5)] == ['CORE_RESET_OK','PC7','GND','CTRL_READY','+3V3_MCU']
    assert [c('U103',p) for p in (2,3,4,5)] == ['NRST','GND','CORE_RESET_OK','+3V3_MCU']
    assert [c('R402',p) for p in (1,2)] == ['PC7','GND']
    assert core['parts']['R402'].findtext('value') == '10k'
    for i, (raw, port) in enumerate([('I_U_PORT','PC0'),('I_V_PORT','PC1'),('I_W_PORT','PC2'),('V_DC_PORT','PC3'),('V_U_PORT','PA4'),('V_V_PORT','PB0'),('V_W_PORT','PB1'),('TEMP_NTC','PB2')]):
        rr, dd, last, cap = f'R{201+i}',f'D{201+i}',f'R{84+i}',f'C{69+i}'
        assert b(rr,1) == raw and b(rr,2) == b(dd,3) == b(last,1)
        assert b(last,2) == b(cap,1) == port and b(cap,2) == 'GND'
        assert [b(dd,p) for p in (1,2)] == ['GND','+3V3_CORE_REF']
    for i,(raw,port) in enumerate([('BASE_READY','PC13'),('FAULT_N','PB12')]):
        assert [b(f'R{210+i}',p) for p in (1,2)] == [raw,port]
        assert [b(f'D{209+i}',p) for p in (1,2,3)] == ['GND','+3V3_CORE_REF',port]
    assert [b('R143',p) for p in (1,2)] == ['PB12','+3V3_CORE_REF']
    assert [b('R209',p) for p in (1,2)] == ['PC13','GND']
    assert b('U4',5) == '+3V3_INV'
    assert b('J13',1) == '+3V3_CORE_REF' and b('J13',5) == 'NRST'
    for ref in [f'Q{i}' for i in range(1,8)]:
        assert len({b(ref,p) for p in (1,2,3)}) == 1, ('MOS source pins',ref)
        assert len({b(ref,p) for p in (5,6,7,8)}) == 1, ('MOS drain pins',ref)
        assert b(ref,4) not in (b(ref,1),b(ref,5)), ('MOS gate short',ref)
    supply_report = json.loads((CORE/'review/core_supply_validation.json').read_text(encoding='utf-8'))
    assert len(supply_report['supply_pin_checks']) == 51 and len(supply_report['arm_pin_checks']) == 9
    supply_count = 0
    for key in ('supply_pin_checks','arm_pin_checks'):
        for row in supply_report[key]:
            ref,pin = row['pin'].split('.')
            assert c(ref,pin) == row['expected'].rsplit('/',1)[-1], ('core supply',row['pin'],row['expected'],c(ref,pin))
            supply_count += 1
    gates = []
    for ref,kind in [(f'U{i}','AND') for i in range(22,27)]+[('U27','NAND')]:
        for a,z,y in [(1,2,3),(4,5,6),(9,10,8),(12,13,11)]:
            out = b(ref,y)
            if not out.startswith('unconnected-'):
                gates.append((b(ref,a),b(ref,z),out,kind))
    def evaluate(inputs):
        values = {'GND':False,'+3V3_INV':True} | inputs
        for _ in range(len(gates)+1):
            for a,z,y,kind in gates:
                if y not in values and a in values and z in values:
                    values[y] = (values[a] and values[z]) if kind=='AND' else not(values[a] and values[z])
        return values
    healthy = [f'OC_{p}_{s}_OK' for p in 'UVW' for s in ('HIGH','LOW')] + ['BUS_OV_OK','DRV_UV_OK','BASE_LOGIC_OK','DRV_PG_LOGIC','AUX_FLT_N']
    cases = 0
    for mask in range(1<<len(healthy)):
        h = {name:bool(mask&(1<<i)) for i,name in enumerate(healthy)}
        for reset in (False,True):
            for arm in (False,True):
                for enable in (False,True):
                    for latch in (False,True):
                        values = evaluate(h | {'ENABLE_IN':enable,'CTRL_READY':reset and arm,'NO_LATCH':not latch} | {f'PWM_{p}_IN':True for p in ('UH','UL','VH','VL','WH','WL')})
                        permit = all(h.values()) and reset and arm and enable and not latch
                        assert values['DRIVE_PERMIT'] == permit
                        assert all(values[p+'_HIN'] == values[p+'_LIN'] == permit for p in 'UVW')
                        cases += 1
    return {'header_contacts':contact_checks,'MCU_signal_pads':52,'supply_pin_assertions':supply_count,'hardware_permission_truth_cases':cases,
            'checks':['NRST and PC7 ARM jointly required','8 ADC and 2 status return clamps use core reference',
                      'two 3.3 V supply domains remain separate','MOS source/drain numbered groups preserved',
                      'RESET and BOOT button paths preserved']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline',type=Path,default=REPO/'outputs/schematic_review_2026-11-11/baseline')
    parser.add_argument('--output',type=Path,default=REPO/'outputs/schematic_review_2026-11-11/system_check.json')
    args = parser.parse_args()
    with (LIB/'parts.csv').open(encoding='utf-8-sig',newline='') as stream:
        shared = {x['Supplier_PN']:x for x in csv.DictReader(stream)}
    contract_path = REPO/'docs/daughterboard_pin_contract.json'
    assert sha(contract_path) == sha(args.baseline/'daughterboard_pin_contract.json'), 'Header contract changed'
    boards, details = {}, {}
    for role, directory in [('controller',CORE),('inverter',BASE)]:
        before = load_netlist(args.baseline/(role+'.net.xml'))
        after = load_netlist(directory/'review'/(role+'.net.xml'))
        details[role] = board_checks(role,before,after,shared)
        erc = json.loads((directory/'review/erc.json').read_text(encoding='utf-8'))
        violations = [v for sheet in erc['sheets'] for v in sheet['violations']]
        assert not violations, (role,'ERC findings',Counter(v['severity'] for v in violations))
        details[role]['erc'] = {'errors':0,'warnings':0,'kicad_version':erc['kicad_version']}
        boards[role] = after
    functional = functional_checks(boards['controller'],boards['inverter'],json.loads(contract_path.read_text(encoding='utf-8')))
    report = {'result':'PASS','date':DATE,'revision':'E-shared-library-draft','boards':details,'functional':functional,
              'scope':'Native KiCad netlist/part/pad and static logic checks; no PCB or hardware qualification.',
              'shared_parts_sha256':sha(LIB/'parts.csv'),'pin_contract_sha256':sha(contract_path)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for directory in (CORE,BASE):
        (directory/'review/system_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'PASS','controller':details['controller']['components'],'inverter':details['inverter']['components'],
        'contacts':64,'GPIO_pads':52,'permission_cases':functional['hardware_permission_truth_cases'],
        'pending':{r:len(d['selection_pending_references']) for r,d in details.items()}},ensure_ascii=False))


if __name__ == '__main__':
    main()
