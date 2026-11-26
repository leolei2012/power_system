#!/usr/bin/env python3
"""2026-11-24只读复核；2026-11-26放行指定文字整理，不导出/改写工程或旧报告。"""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
from decimal import Decimal as D

ROOT = Path(__file__).resolve().parents[4]
BASE = Path('controller/hardware/g431_core')
REVIEW = BASE / 'review'
HEAD = '54c28460baaf011a00254aa97edbb213a8b3e167'
ARCHIVE = Path('/workspace/work/prompts/m1_preserved_20261124/inherited_files.tar.gz')
ALLOWED = {
    str(BASE / 'core_supply_design.md'), 'docs/controller_daughterboard.md',
    str(REVIEW / 'issue2_changes.md'), str(REVIEW / 'm1_local_preparation_20261124.md'),
    str(REVIEW / 'verify_m1_local_20261124.py'),
    str(BASE / 'core_supply.kicad_sch'), str(BASE / 'comms.kicad_sch'),
    str(REVIEW / 'bom_issue2.csv'), 'docs/pinmap.md',
}
# 2026-11-26编辑前，将原快照排除上述4个新增文字变更文件后重算；其余冻结范围不变。
# 两张放行原理图及D102 BOM行另按保全包/HEAD核对，仅允许下列注解/状态字段变化。
FROZEN = {
    '受保护文件全集': (2241, '636948e43ea7b8bceab23856f5387e996caba8ff27c1fa82c4095091c2cfa8e1'),
    '所有电路和PCB': (298, '184041df3e01e728f1952e4da6428a2071f56ea4f3496f76f26f174e1608fb97'),
    '共享库子模块': (617, 'd3e2a12374e89bdeeb63181705da3e8c6d71868de3502d73ca14492cdb34e473'),
    'inverter': (1147, '6a1766f3a2adcbd939bc27d8d0628ad23fcf0db0f0f48f1fec1705f959b399a1'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT,
                                   env=os.environ | {'GIT_OPTIONAL_LOCKS': '0'})


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parse(text):
    """解析 KiCad S 表达式；不执行原有验证脚本，也不加载 KiCad Python。"""
    stack, root = [], None
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        if token == '(':
            node = []
            if stack:
                stack[-1].append(node)
            else:
                root = node
            stack.append(node)
        elif token == ')':
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    require(not stack and root is not None, 'S表达式不完整')
    return root


def children(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def one(node, key):
    return next(iter(children(node, key)), None)


def props(node):
    return {x[1]: x[2] for x in children(node, 'property')}


def annotation_view(raw, filename):
    """只屏蔽指定图注内容及D102状态文字；其余器件/位置/网络/封装均须完全一致。"""
    page = parse(raw.decode())
    note_ids = {
        'core_supply.kicad_sch': {'7dd45490-29a7-524e-858b-1969f939b3d0',
                                '046f474e-77de-500c-80c7-af945ac0f1cb'},
        'comms.kicad_sch': {'fedd22ea-cc65-5845-a167-52097fdf079a'},
    }[filename]
    found = set()
    for note in children(page, 'text'):
        uid = one(note, 'uuid')[1]
        if uid in note_ids:
            found.add(uid)
            note[1] = '<允许修改的图注文字>'
    require(found == note_ids, filename + '指定图注缺失')
    if filename == 'core_supply.kicad_sch':
        candidates = [s for s in children(page, 'symbol') if props(s).get('Reference') == 'D102']
        require(len(candidates) == 1, 'D102实例不唯一')
        symbol = candidates[0]
        for field in children(symbol, 'property'):
            if field[1] in ('Value', 'Selection_Status', 'Verification'):
                field[2] = '<允许修改的候选状态文字>'
            elif field[1] == 'Design_Note':
                require(one(field, 'hide') == ['hide', 'yes'], 'D102 Design_Note须为隐藏说明')
                symbol.remove(field)
    return page


def bom_annotation_view(raw):
    """仅屏蔽D102 Value说明；其余行保留原字节，D102其他列保留原字段。"""
    lines, count = raw.splitlines(keepends=True), 0
    for i, line in enumerate(lines):
        row = next(csv.reader([line.decode()]))
        if row and row[0] == 'D102':
            row[1] = '<允许修改的候选说明>'
            ending = b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
            lines[i] = json.dumps(row, ensure_ascii=False).encode() + ending
            count += 1
    require(count == 1, '审查BOM的D102行不唯一')
    return b''.join(lines)


def pins(node):
    for x in node:
        if isinstance(x, list):
            if x and x[0] == 'pin' and one(x, 'at'):
                yield x
            else:
                yield from pins(x)


def point(x, y):
    return round(float(x) * 1000000), round(float(y) * 1000000)


def trace(page):
    """由缓存符号引脚、坐标、导线、连接点及同名标签独立追踪本任务所涉局部网络。"""
    libs = {x[1]: x for x in children(one(page, 'lib_symbols'), 'symbol')}
    parent, segments, labels, pin_points, components = {}, [], [], {}, {}

    def find(p):
        parent.setdefault(p, p)
        if parent[p] != p:
            parent[p] = find(parent[p])
        return parent[p]

    def union(a, b):
        parent[find(a)] = find(b)

    for w in children(page, 'wire'):
        a, b = [point(*x[1:3]) for x in children(one(w, 'pts'), 'xy')]
        segments.append((a, b))
        union(a, b)
    for j in children(page, 'junction'):
        find(point(*one(j, 'at')[1:3]))
    for kind in ('label', 'global_label', 'hierarchical_label'):
        for node in children(page, kind):
            p = point(*one(node, 'at')[1:3])
            find(p)
            labels.append((p, node[1]))
    for s in children(page, 'symbol'):
        pr = props(s)
        ref, lib_id = pr['Reference'], one(s, 'lib_id')[1]
        ox, oy, angle = map(float, one(s, 'at')[1:4])
        require(one(s, 'mirror') is None, '局部追踪暂不支持镜像：' + ref)
        angle = math.radians(angle)
        pin_names = {}
        for pin in pins(libs[lib_id]):
            x, y = map(float, one(pin, 'at')[1:3])
            p = point(ox + x * math.cos(angle) - y * math.sin(angle),
                      oy - x * math.sin(angle) - y * math.cos(angle))
            num = one(pin, 'number')[1]
            pin_names[num] = one(pin, 'name')[1]
            find(p)
            if not ref.startswith('#'):
                pin_points[(ref, num)] = p
            elif lib_id.startswith('power:') and lib_id != 'power:PWR_FLAG':
                labels.append((p, pr['Value']))
        if not ref.startswith('#'):
            components[ref] = {'字段': pr, '引脚名': pin_names,
                               'DNP': one(s, 'dnp')[1]}
    # 仅连接已有端点/引脚/标签/显式连接点；无连接点的两根交叉导线不凭空相连。
    for a, b in segments:
        for p in list(parent):
            if ((p[0]-a[0])*(b[1]-a[1]) == (p[1]-a[1])*(b[0]-a[0])
                    and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                    and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])):
                union(a, p)
    by_name = {}
    for p, name in labels:
        if name in by_name:
            union(p, by_name[name])
        by_name[name] = p
    names = {}
    for p, name in labels:
        names.setdefault(find(p), set()).add(name)
    require(all(len(v) == 1 for v in names.values()), '局部网络出现异名短接')
    nodes = {key: next(iter(names.get(find(p), {''}))) for key, p in pin_points.items()}
    return nodes, components


def calculations():
    rows = []
    for vin in map(D, ('4.75', '5.00')):
        for i in map(D, ('.275', '.325')):
            drop = D('.47') * (i + D('.0024'))
            need = D('3.333') + D('1.4') * i
            vf_limit = vin - drop - need
            rows.append({'入口V': str(vin), '负载mA': str(i*1000),
                         'R301压降V': str(drop), 'LDO需求V': str(need),
                         'S1A入口V': str(vin-drop-D('1.1')),
                         'S1A余量V': str(vf_limit-D('1.1')),
                         'PMEG借用室温点余量V': str(vf_limit-D('.32')),
                         'PMEG冷态假设余量V': str(vf_limit-D('.42')),
                         'VF允许上限零储备V': str(vf_limit),
                         'VF允许上限0.2V储备V': str(vf_limit-D('.2'))})
    aux_examples = []
    for vin in map(D, ('4.75', '5.25')):
        r, rsum, i, ignd = D('.4747'), D('2079'), D('.325'), D('.0015')
        vtvs = (vin-r*(i+ignd))/(1+r/rsum)
        aux_examples.append({'入口V': str(vin), '输出mA': '325', 'VTVS_V': str(vtvs),
                             'IMR_mA': str(vtvs/rsum*1000), 'Iaux_mA': str((ignd+vtvs/rsum)*1000),
                             'S1A余量V': str(vtvs-D('1.1')-D('3.333')-D('1.4')*i),
                             'PMEG冷态假设余量V': str(vtvs-D('.42')-D('3.333')-D('1.4')*i)})
    tolerance = [{'输出mA': str(i*1000),
                  'R301正1%余量减少mV': str(D('.0047')*(i+D('.0024'))*1000),
                  '支路额外100毫欧余量减少mV': str(D('.1')*(i+D('.0024'))*1000)}
                 for i in map(D, ('.275', '.325'))]
    return {'条件': 'Iaux=2.4mA、R301标称、附加接触压降=0；不构成全温保证',
            '四点': rows,
            '公差和线阻敏感性': tolerance,
            '辅助支路示例_IGND仅借用典型_其余漏电未计': aux_examples,
            'S1A_325mA零余量入口V': str(D('3.333')+D('1.4')*D('.325')+D('.47')*D('.3274')+D('1.1')),
            'S1A_4.75V零余量电流mA': str((D('4.75')-D('3.333')-D('1.1')-D('.47')*D('.0024'))/(D('1.4')+D('.47'))*1000),
            '双终端680偏置mV': str(D('3.3')*60/(680+680+60)*1000),
            '辅助电流每增加10mA余量减少V': str(D('.47')*D('.010')),
            '输出电流每增加10mA余量减少V_未计VF变化': str((D('.47')+D('1.4'))*D('.010'))}


def main():
    require(git('rev-parse', 'HEAD').decode().strip() == HEAD, 'HEAD偏离审批基线')
    require(git('branch', '--show-current').decode().strip() == 'hw/controller-fixes-issue2', '分支不符')
    fs = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in ROOT.rglob('*')
          if '.git' not in p.relative_to(ROOT).parts and p.is_file()}
    groups = {
        '受保护文件全集': {p: h for p, h in fs.items() if p not in ALLOWED},
        '所有电路和PCB': {p: h for p, h in fs.items() if Path(p).suffix in ('.sch', '.kicad_sch', '.kicad_pcb', '.pcb') and p not in ALLOWED},
        '共享库子模块': {p: h for p, h in fs.items() if p.startswith('lib/kicad_library/')},
        'inverter': {p: h for p, h in fs.items() if p.startswith('inverter/')},
    }
    digests = {}
    for name, files in groups.items():
        digest = sha(''.join(p+'\0'+h+'\n' for p, h in sorted(files.items())).encode())
        require((len(files), digest) == FROZEN[name], name + '与本轮前快照不一致')
        digests[name] = {'文件数': len(files), 'SHA256': digest, '与本轮前一致': True}
    snapshot, inherited = {}, {}
    with tarfile.open(ARCHIVE, 'r:gz') as archive:
        for member in archive.getmembers():
            if member.isfile():
                name = member.name.removeprefix('./')
                original = archive.extractfile(member).read()
                old_sha = sha(original)
                if name in (str(BASE / 'core_supply.kicad_sch'), str(REVIEW / 'bom_issue2.csv')):
                    inherited[name] = original
                snapshot[name] = {'保全SHA256': old_sha, '当前SHA256': fs.get(name),
                                  '本轮允许改文档或注解': name in ALLOWED}
                if name not in ALLOWED:
                    require(fs.get(name) == old_sha, '继承文件字节改变：' + name)
    bom_name = str(REVIEW / 'bom_issue2.csv')
    require(bom_annotation_view((ROOT / bom_name).read_bytes()) == bom_annotation_view(inherited[bom_name]),
            '审查BOM存在D102 Value说明之外的变更')
    import xml.etree.ElementTree as ET
    xml = ET.parse(ROOT / REVIEW / 'controller.net.xml')
    xml_nodes = {(n.get('ref'), n.get('pin')): net.get('name').rsplit('/', 1)[-1]
                 for net in xml.findall('./nets/net') for n in net.findall('node')}
    xml_comps = {c.get('ref'): c for c in xml.findall('./components/comp')}
    current, baseline, details, source_hashes = {}, {}, {}, {}
    for filename in ('core_supply.kicad_sch', 'comms.kicad_sch', 'core_interface.kicad_sch'):
        rel = BASE / filename
        raw, old = (ROOT / rel).read_bytes(), git('show', HEAD + ':' + str(rel))
        if filename in ('core_supply.kicad_sch', 'comms.kicad_sch'):
            original = inherited[str(rel)] if filename == 'core_supply.kicad_sch' else old
            require(annotation_view(raw, filename) == annotation_view(original, filename),
                    filename + '存在指定图注/D102状态字段之外的变更')
        now_nodes, now_comps = trace(parse(raw.decode()))
        old_nodes, old_comps = trace(parse(old.decode()))
        require(now_nodes == old_nodes, filename + '局部网络偏离HEAD')
        current.update(now_nodes)
        baseline.update(old_nodes)
        details.update(now_comps)
        source_hashes[filename] = {'HEAD_SHA256': sha(old), '工作树SHA256': sha(raw)}
        if filename == 'core_supply.kicad_sch':
            require(old_comps['D102']['字段']['Value'] == 'S1A-13-F', '审批基线D102不符')
            for comps in (old_comps, now_comps):
                require(comps['D102']['引脚名'] == {'1': 'K', '2': 'A'}, 'D102极性不符')
    expected = {
        'J101': {'1': '+5V_CORE_IN', '3': '+5V_CORE_IN'},
        'R301': {'1': '+5V_CORE_IN', '2': 'CORE_5V_TVS'},
        'D101': {'1': 'CORE_5V_TVS', '2': 'GND'},
        'D102': {'1': 'CORE_LDO_IN', '2': 'CORE_5V_TVS'},
        'D103': {'1': 'CORE_LDO_IN', '2': '+3V3_MCU'},
        'U101': {'1': '+3V3_MCU', '2': '+3V3_MCU', '3': 'GND', '4': 'CORE_LDO_IN',
                 '5': 'GND', '6': 'CORE_LDO_IN', '7': 'GND'},
        'C301': {'1': 'CORE_5V_TVS', '2': 'GND'},
        'C302': {'1': 'CORE_LDO_IN', '2': 'GND'},
        'C303': {'1': '+3V3_MCU', '2': 'GND'},
        'C304': {'1': '+3V3_MCU', '2': 'GND'},
        'C305': {'1': '+3V3_MCU', '2': 'GND'},
        'R304': {'1': 'CORE_5V_TVS', '2': 'CORE_MR_5V_PRESENT'},
        'R305': {'1': 'CORE_MR_5V_PRESENT', '2': 'GND'},
        'U102': {'3': 'CORE_MR_5V_PRESENT'},
        'U203': {'1': '+5V_CORE_IN', '2': 'GND', '3': '+5V_CORE_IN', '5': 'TPS2553_ILIM', '6': '5V_OUT_LIM'},
        'C211': {'1': '+5V_CORE_IN', '2': 'GND'},
        'C212': {'1': '5V_OUT_LIM', '2': 'GND'},
        'R227': {'1': 'TPS2553_ILIM', '2': 'GND'},
        'D201': {'1': '5V_OUT', '2': '5V_OUT_LIM'},
        'J201': {'4': '5V_OUT'},
        'R228': {'1': '+3V3_MCU', '2': 'RS485_A'},
        'R229': {'1': 'RS485_B', '2': 'GND'},
    }
    count = 0
    for ref, ref_pins in expected.items():
        require(details[ref]['字段']['Footprint'] == xml_comps[ref].findtext('footprint'), 'XML封装不符：' + ref)
        for pin, name in ref_pins.items():
            require(current.get((ref, pin)) == baseline.get((ref, pin)) == xml_nodes.get((ref, pin)) == name,
                    '三方路径不符：' + ref + '/' + pin)
            count += 1
    require(details['D102']['字段']['MPN'] == 'PMEG2010ER,115', '继承候选D102型号不符')
    require(all(details[r]['DNP'] == 'yes' for r in ('R228', 'R229')), '485默认DNP不符')
    require(not any(r.startswith(('F', 'FB', 'L')) for r in details if r not in ('J101', 'J102')), '局部页有需人工追踪的保险/磁珠/电感')
    gitlink = next(line.split()[1].decode() for line in git('ls-files', '--stage', '--', 'lib/kicad_library').splitlines()
                   if line.startswith(b'160000 '))
    submodule_head = git('-C', 'lib/kicad_library', 'rev-parse', 'HEAD').decode().strip()
    require(gitlink == submodule_head == '1dd8f79eab18ff2b302ee1c7d614079549088824', '子模块HEAD或gitlink改变')
    result = {'结论': '本轮路径/计算/字节保全复核通过；D102验证路线已批准，候选料号未定案，M1仍待电气验证',
              'HEAD': HEAD, '来源原理图哈希': source_hashes,
              '路径核对': {'所涉页': 3, '三方引脚数': count, 'XML性质': '已有候选XML，非本轮重新导出',
                         'XML工具': xml.findtext('./design/tool'), 'XML日期': xml.findtext('./design/date'),
                         '逐项网络': expected, '默认偏置': 'R228/R229均DNP'},
              'ERC环境': {'kicad-cli': shutil.which('kicad-cli'), '/opt/kicad存在': Path('/opt/kicad').exists(),
                          '本轮ERC': '无法重跑；未安装或切换版本；旧0/0仅为历史候选结果'},
              '计算': calculations(), '本轮前后保全摘要': digests,
              '11份继承快照比较': snapshot,
              '保全压缩包SHA256': sha(ARCHIVE.read_bytes()),
              '保全补丁SHA256': sha(ARCHIVE.with_name('diff.patch').read_bytes()),
              '子模块HEAD及gitlink': submodule_head}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
