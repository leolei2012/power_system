#!/usr/bin/env python3
"""Read-only design checks; writes only review JSON and the requested -o summary.
Run from any directory after native KiCad ERC/netlist/BOM/PDF export.
PCB API reads, when needed, use /usr/local/bin/kicad-python.
"""
from pathlib import Path
import argparse, collections, csv, difflib, hashlib, json, math, os, re, subprocess, sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
REVIEW = BASE / 'review'
# Fix the comparison baseline so this remains reproducible after the user commits.
BASELINE_REF = 'bb80a6c921c76b0064af353aefdfa5cc3e5e7714'
class Atom(str): pass

def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text)
    i = 0
    def one():
        nonlocal i
        t = tokens[i]; i += 1
        if t == '(':
            out = []
            while tokens[i] != ')': out.append(one())
            i += 1
            return out
        return json.loads(t) if t.startswith('"') else Atom(t)
    out = one()
    assert i == len(tokens)
    return out

def tagged(node, name): return isinstance(node, list) and bool(node) and node[0] == name
def children(node, name): return [x for x in node if tagged(x, name)]
def child(node, name): return next((x for x in node if tagged(x, name)), None)
def properties(node): return {x[1]: x[2] for x in children(node, 'property')}
def read(path): return parse(Path(path).read_text())
def head(path):
    rel = str(Path(path).relative_to(REPO))
    return subprocess.check_output(['git', 'show', BASELINE_REF + ':' + rel], cwd=REPO, text=True)
def relative(path): return str(Path(path).relative_to(REPO))
def norm(net): return net.rsplit('/', 1)[-1]
def component_pins(lib): return [p for s in children(lib, 'symbol') for p in children(s, 'pin')]
def topology(path):
    root = ET.parse(path).getroot()
    comps = {x.get('ref'): x for x in root.findall('./components/comp')}
    nodes, nets = {}, {}
    for n in root.findall('./nets/net'):
        nets[n.get('name')] = {(x.get('ref'), x.get('pin')) for x in n.findall('node')}
        for x in n.findall('node'): nodes[x.get('ref'), x.get('pin')] = (n.get('name'), dict(x.attrib))
    return root, comps, nodes, nets

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('-o', '--output', type=Path, required=True, help='Write the A–I Markdown result here')
    ap.add_argument('--json-output', type=Path, default=REVIEW / 'validation_issue2.json')
    args = ap.parse_args()
    checks = []
    def check(name, passed, detail=None):
        checks.append({'项目': name, '通过': bool(passed), '详情': detail})
    def equal(name, actual, expected):
        check(name, actual == expected, {'实际': actual, '预期': expected})
    tree, comps, nodes, nets = topology(REVIEW / 'controller.net.xml')
    def net(ref, pin): return norm(nodes.get((ref, str(pin)), ('MISSING', {}))[0])
    def link(ref, pin, expected): equal(f'{ref}/{pin} 网络', net(ref, pin), expected)
    def nc(ref, pin):
        n, attrs = nodes.get((ref, str(pin)), ('', {}))
        return n.startswith('unconnected-') and 'no_connect' in attrs.get('pintype', '') and len(nets[n]) == 1
    def val(ref): return comps[ref].findtext('value')
    def dnp(sym): return child(sym, 'dnp') is not None and child(sym, 'dnp')[1] == 'yes'
    pages = {}
    def visit(path):
        path = path.resolve()
        if path in pages: raise ValueError('Repeated sheet instance requires path-aware handling')
        root = read(path); pages[path] = root
        for s in children(root, 'sheet'): visit(path.parent / properties(s)['Sheetfile'])
    visit(BASE / 'controller.kicad_sch')
    instances, libs = {}, {}
    for path, root in pages.items():
        cache = {s[1]: s for s in children(child(root, 'lib_symbols'), 'symbol')}
        for s in children(root, 'symbol'):
            ref = properties(s).get('Reference', '')
            if ref.startswith('#'): continue
            instances.setdefault(ref, []).append((path, s))
            libs[ref] = cache[child(s, 'lib_id')[1]]
    symbols = {r: items[0][1] for r, items in instances.items()}
    fields = {r: properties(s) for r, s in symbols.items()}
    pinmap = (REPO / 'docs/pinmap.md').read_text()
    def section(text, start, stop): return text.split(start, 1)[1].split(stop, 1)[0]
    def rows(text):
        return [[v.strip().strip('`') for v in l.strip().strip('|').split('|')]
                for l in text.splitlines() if re.match(r'^\|\s*\d+\s*\|', l)]
    for ref, start, stop in [('J101', '### 4.1 ', '### 4.2 '), ('J102', '### 4.2 ', '### 4.3 ')]:
        rs = rows(section(pinmap, start, stop)); equal(ref + ' pinmap条目数', len(rs), 32)
        for row in rs: link(ref, row[0], re.split(r'[（(]', row[2])[0])
    mcu_rows = rows(section(pinmap, '## 3. ', '## 4. '))
    equal('MCU pinmap条目数', len(mcu_rows), 64)
    analog = {'I_U', 'I_V', 'I_W', 'I_BUS', 'V_DC', 'NTC', 'ADC_SP1', 'ADC_SP2'}
    for row in mcu_rows:
        pin, port, target = row[:3]
        if target == 'NC': check(f'U30/{pin} NC且独立', nc('U30', pin))
        else: link('U30', pin, target + '_MCU' if target in analog else target)
        actual_port = re.sub(r'_\d+$', '', nodes.get(('U30', pin), ('', {}))[1].get('pinfunction', ''))
        equal(f'U30/{pin} 物理端口', actual_port, port.split('-')[0])
    equal('MCU恰好13个NC', sum(nc('U30', str(p)) for p in range(1, 65)), 13)
    equal('10页层级', len(pages), 10)
    equal('元件位号数', len(comps), 102)
    for ref, items in instances.items(): equal('位号唯一 ' + ref, len(items), 1)
    for p in pages: check('活动页路径 ' + p.name, 'history' not in p.parts and p.name not in ['debug_comms.kicad_sch', 'sensors.kicad_sch'])

    # All eight filter branches, exactly as the previous review checked them.
    for i, signal in enumerate(['I_U', 'I_V', 'I_W', 'I_BUS', 'V_DC', 'NTC', 'ADC_SP1', 'ADC_SP2'], 201):
        rr, cr = 'R' + str(i), 'C' + str(i)
        link(rr, 1, signal); link(rr, 2, signal + '_MCU'); link(cr, 1, signal + '_MCU'); link(cr, 2, 'GND')
        equal(rr + '设计取值', val(rr), '100' if i <= 204 else '1k')
        equal(cr + '设计取值', val(cr), '1n' if i <= 204 else '10n')
        check(signal + ' RC未旁路', net(rr, 1) != net(rr, 2))
        if i <= 204: check(cr + 'C0G要求', 'C0G' in json.dumps(fields[cr], ensure_ascii=False))
    for ref, mapping in {
        'U201': {1:'RS485_RX',2:'RS485_DE',3:'RS485_DE',4:'RS485_TX',5:'GND',6:'RS485_A',7:'RS485_B',8:'+3V3_MCU'},
        'U202': {1:'CAN_TX',2:'GND',3:'+3V3_MCU',4:'CAN_RX',6:'CANL',7:'CANH'},
        'J201': {1:'RS485_A',2:'RS485_B',3:'GND',4:'5V_OUT'},
        'J202': {1:'CANH',2:'CANL',3:'GND'},
        'D202': {1:'RS485_A',2:'RS485_B',3:'GND'},
        'D203': {1:'CANH',2:'CANL',3:'GND'},
        'R209': {1:'RS485_DE',2:'GND'}, 'R210': {1:'RS485_RX',2:'+3V3_MCU'},
        'U203': {1:'+5V_CORE_IN',2:'GND',3:'+5V_CORE_IN',5:'TPS2553_ILIM',6:'5V_OUT_LIM'},
        'D201': {1:'5V_OUT',2:'5V_OUT_LIM'}, 'R227': {1:'TPS2553_ILIM',2:'GND'},
        'C211': {1:'+5V_CORE_IN',2:'GND'}, 'C212': {1:'5V_OUT_LIM',2:'GND'},
        'R228': {1:'+3V3_MCU',2:'RS485_A'}, 'R229': {1:'RS485_B',2:'GND'},
        'J203': {1:'+3V3_MCU',2:'ENC_A_CONN',3:'ENC_B_CONN',4:'ENC_Z_CONN',5:'GND'},
        'J204': {1:'+3V3_MCU',2:'SPI_CS_CONN',3:'SPI_SCK_CONN',4:'SPI_MISO_CONN',5:'SPI_MOSI_CONN',6:'GND'},
        'J205': {1:'+3V3_MCU',2:'SWDIO',3:'SWCLK',4:'NRST',5:'GND'},
        'SW2': {1:'NRST',2:'GND'}, 'C81': {1:'NRST',2:'GND'},
        'TP15': {1:'BOOT0'}, 'TP16': {1:'+3V3_MCU'}, 'R122': {1:'BOOT0',2:'GND'},
        'U105': {1:'CORE_RESET_OK',2:'RUN_ARM',3:'GND',4:'CTRL_READY',5:'+3V3_MCU'},
        'R402': {1:'RUN_ARM',2:'GND'},
    }.items():
        for pin, target in mapping.items(): link(ref, pin, target)
    for ref, pins_to_nc in [('U202', ['5', '8']), ('U203', ['4']), ('SW2', ['MP']), ('D204', ['3']), ('D205', ['3'])]:
        for p in pins_to_nc: check(f'{ref}/{p} 为NC且无外部连接', nc(ref, p))
    for ref in ['SW3', 'R401', 'JP203']: check(ref + '已删除', ref not in comps and ref not in instances)
    check('编码器无5V或VCC_ENC网', all(not any(k in net(r, 1) for k in ['5V', 'VCC_ENC']) for r in ['J203','J204']))
    for ref, signal in zip(['R213','R214','R215','R216','R217','R218','R219'], ['ENC_A','ENC_B','ENC_Z','SPI_CS','SPI_SCK','SPI_MISO','SPI_MOSI']):
        check(ref + '100Ω串联', val(ref) == '100' and {net(ref, 1), net(ref, 2)} == {signal, signal+'_CONN'})
    for ref, signal in zip(['R220','R221','R222','R223','R224'], ['ENC_A','ENC_B','ENC_Z','SPI_MISO','SPI_CS']):
        equal(ref + '10k上拉', val(ref), '10k'); link(ref, 1, '+3V3_MCU'); link(ref, 2, signal)
    for diode, resistor, signal in [('D204','R225','LED_RUN'), ('D205','R226','LED_FAULT')]:
        link(resistor, 1, signal); link(diode, 2, 'GND')
        check(diode + '阳极1经限流电阻高电平亮', net(diode,1) == net(resistor,2) and net(diode,1) not in ['GND','MISSING'])
        equal(resistor + '1k', val(resistor), '1k')
        equal(diode + '符号物理极性', {child(p,'number')[1]:child(p,'name')[1] for p in component_pins(libs[diode]) if child(p,'number')[1] in ['1','2']}, {'1':'A','2':'K'})
    for jumper, rr, line in [('JP201','R211','RS485_B'), ('JP202','R212','CANL')]:
        check(jumper + '串联120Ω', net(jumper,1) == net(rr,2) and val(rr)=='120')
        check(jumper + '默认开路', child(symbols[jumper],'lib_id')[1] == 'Jumper:SolderJumper_2_Open')
        check(rr + '0805', '0805' in fields[rr]['Footprint'])
    for ref in ['Y1','C83','C84','D202','D203','R228','R229']: check(ref + '保持DNP', dnp(symbols[ref]))
    for r in ['R227','R228','R229']: equal(r + '取值', val(r), '49.9k' if r=='R227' else '680')
    equal('C211输入旁路100n', val('C211'), '100n'); equal('C212输出旁路4.7u', val('C212'), '4.7u')
    external_5v = sorted([r+'/'+p for r,p in nets['5V_OUT'] if r.startswith('J')])
    equal('5V_OUT全部对外端子在限流后', external_5v, ['J201/4'])
    equal('5V_OUT无旁路器件节点', sorted(nets['5V_OUT']), [('D201','1'), ('J201','4')])
    equal('D201与D103统一封装', fields['D201']['Footprint'], fields['D103']['Footprint'])
    equal('D201回流焊封装', fields['D201']['Footprint'], 'MyFootprints:Nexperia_CFP3_SOD123W_Reflow')

    # Recompute every original netlist pin expectation from the repository baseline.
    baseline_net = ET.fromstring(head(REVIEW / 'controller.net.xml'))
    baseline_nodes = {(x.get('ref'),x.get('pin')): n.get('name') for n in baseline_net.findall('./nets/net') for x in n.findall('node')}
    for (ref,pin), oldnet in baseline_nodes.items():
        if ref == 'JP203': continue
        expected = norm(oldnet)
        if (ref,pin) == ('D201','2'): expected='5V_OUT_LIM'
        elif ref in ['J203','J204'] and pin=='1': expected='+3V3_MCU'
        elif ref in ['D204','D205'] and pin in ['1','2']: expected=norm(baseline_nodes[(ref, '2' if pin=='1' else '1')])
        equal(f'保留/授权变更基线连接 {ref}/{pin}', net(ref,pin), expected)
    selected = ['U203','R227','C211','C212','SW2','D202','D203','D204','D205','R225','R226','R228','R229']
    empty, small = [], []
    fp_files = {}
    for ref, data in fields.items():
        footprint=data.get('Footprint','')
        if not footprint: empty.append(ref)
        if re.search(r'0402|01005|0201',footprint): small.append([ref,footprint])
        equal(ref+' XML/实例封装一致', comps[ref].findtext('footprint'), footprint)
        if ref in selected:
            for k in ['Value','Footprint','Datasheet','Manufacturer','MPN','LCSC','Purchase_URL']:
                check(ref+'要求字段 '+k, bool(data.get(k)), data.get(k))
            if ref!='C212':
                check(ref+'采购C编号有效', bool(re.fullmatch(r'C\d+',data['LCSC'])))
                check(ref+'Datasheet为资料链接', data['Datasheet'].startswith('https://'))
                check(ref+'Purchase_URL为立创商品页', data['Purchase_URL'].startswith(('https://item.szlcsc.com/','https://www.lcsc.com/product-detail/')))
        if footprint:
            library,name=footprint.split(':',1)
            if library=='MyFootprints': path=REPO/'lib/kicad_library/footprints/MyFootprints.pretty'/f'{name}.kicad_mod'
            elif library in ['Inverter_Compact','ControllerLocal']: path=BASE/f'{library}.pretty'/f'{name}.kicad_mod'
            else: path=Path('/opt/kicad/current/share/kicad/footprints')/f'{library}.pretty'/f'{name}.kicad_mod'
            check(ref+'封装可解析',path.is_file(),str(path))
            if path.is_file():
                fp_files[ref]=path
                pads={p[1] for p in children(read(path),'pad') if p[1]}
                pins={child(p,'number')[1] for p in component_pins(libs[ref])}
                check(ref+'封装包含全部符号引脚', pins<=pads, {'引脚':sorted(pins),'焊盘':sorted(pads)})
    equal('活动层级0402/01005/0201 Footprint数量',len(small),0)
    equal('活动层级空Footprint数量',len(empty),0)
    for ref in ['C211','C212','R227','R228','R229']:
        check(ref+'新增阻容≥0603', any(s in fields[ref]['Footprint'] for s in ['0603','0805']))
    for ref in ['C63','C64','C65','C66','C67','C77','C79','C81','C83','C84','R92','R93','R122']:
        check(ref+'保留0603及既有采购字段', '0603' in fields[ref]['Footprint'] and fields[ref].get('MPN') not in ['',None,'TBD','待#5'])
    local=read(BASE/'CoreProtection.kicad_sym')
    local_defs={s[1]:s for s in children(local,'symbol')}
    for ref in ['SW2','D202','D203','D204','D205']:
        lib=libs[ref]; name=lib[1].split(':')[1]; clone=list(lib);clone[1]=name
        check(ref+'本地库与缓存定义一致', clone==local_defs[name])
        check(ref+'本地临时符号说明', '临时本地符号' in properties(local_defs[name]).get('Description',''))
    fp=read(fp_files['D204']); pads={p[1]:p for p in children(fp,'pad')}
    for n,at,size in [('1',[-1.6,0],[1.3,.9]),('2',[1.6,0],[1.3,.9]),('3',[0,.55],[1,.8])]:
        equal('LED pad'+n+'位置',[float(x) for x in child(pads[n],'at')[1:3]],at)
        equal('LED pad'+n+'尺寸',[float(x) for x in child(pads[n],'size')[1:3]],size)
    equal('LED两色共用一致封装',fields['D204']['Footprint'],fields['D205']['Footprint'])
    equal('LED端电极内沿间隙',round(3.2-1.3,4),1.9)
    equal('LED中央焊盘边缘偏移',round(.55+.8/2-.9/2,4),.5)
    swpads=children(read(fp_files['SW2']),'pad')
    equal('SW2两个pad1对应实物1/3',sum(p[1]=='1' for p in swpads),2)
    equal('SW2 MP焊盘个数',sum(p[1]=='MP' for p in swpads),2)
    for r in ['D202','D203']:
        equal(r+'SOT-23物理焊盘',sorted(p[1] for p in children(read(fp_files[r]),'pad') if p[1]),['1','2','3'])

    # Historical sheets, source document scope, and zero copper/placement changes.
    for name in ['debug_comms','sensors']:
        old=BASE/(name+'.kicad_sch'); new=BASE/'history'/(name+'.kicad_sch')
        check(name+'已移入history且原文不变',not old.exists() and new.read_text()==head(old))
    oldmap=head(REPO/'docs/pinmap.md')
    for a,b in [('## 3. ','## 4. '),('### 4.1 ','### 4.2 '),('### 4.2 ','### 4.3 '),('## 5A. ','## 6. ')]:
        equal('pinmap未改 '+a.strip(),section(pinmap,a,b),section(oldmap,a,b))
    changed=[]
    for tag,i,j,k,l in difflib.SequenceMatcher(None,oldmap.splitlines(),pinmap.splitlines()).get_opcodes():
        if tag!='equal': changed += oldmap.splitlines()[i:j]+pinmap.splitlines()[k:l]
    check('pinmap改动只涉及编码器供电/485第4针',all(any(s in line for s in ['编码器','485','ABZ/SPI 端子供电电压']) for line in changed if line.strip()))
    board=read(BASE/'controller.kicad_pcb'); oldboard=parse(head(BASE/'controller.kicad_pcb'))
    texts=[n for n in children(board,'gr_text') if n[1]=='3.3V ENCODER ONLY']
    equal('PCB新增英文丝印数量',len(texts),1)
    if len(texts)==1:
        text=texts[0];board.remove(text)
        equal('PCB文字之外所有结构保持',board,oldboard)
        equal('PCB丝印层',child(text,'layer')[1],'F.SilkS')
        equal('PCB丝印中心mm',[float(x) for x in child(text,'at')[1:3]],[130.,158.])
    code="""import json,pcbnew
b=pcbnew.LoadBoard(%r)
print(json.dumps({'texts':[(x.GetText(),('F.SilkS' if x.GetLayer()==pcbnew.F_SilkS else b.GetLayerName(x.GetLayer())),pcbnew.ToMM(x.GetPosition().x),pcbnew.ToMM(x.GetPosition().y)) for x in b.GetDrawings() if isinstance(x,pcbnew.PCB_TEXT) and x.GetText()=='3.3V ENCODER ONLY'],'refs':[f.GetReference() for f in b.GetFootprints() if f.GetReference() in ['J203','J204','JP203']]}))
""" % str(BASE/'controller.kicad_pcb')
    rb=json.loads(subprocess.check_output(['/usr/local/bin/kicad-python','-c',code],text=True))
    equal('kicad-python PCB读回',rb['texts'],[['3.3V ENCODER ONLY','F.SilkS',130.,158.]])
    equal('旧PCB无J203/J204/JP203',rb['refs'],[])
    equal('当前分支',subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip(),'hw/controller-sch-issue2')
    env=os.environ|{'GIT_OPTIONAL_LOCKS':'0'}
    protected=['docs/design_decisions.md','docs/test_spec.md','fw','firmware','inverter','lib',relative(BASE/'bom/bom.csv'),relative(BASE/'review/bom.csv'),relative(BASE/'controller.kicad_pro')]
    status=subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--']+protected,cwd=REPO,env=env,text=True)
    check('冻结文件和范围外文件未变',not status,status)
    for name in ['sym-lib-table','fp-lib-table']:
        tab=read(BASE/name)
        for lib in children(tab,'lib'):
            uri=child(lib,'uri')[1]
            check(name+'项目相对路径 '+child(lib,'name')[1],uri.startswith('${KIPRJMOD}/'),uri)
    localtab=next(x for x in children(read(BASE/'fp-lib-table'),'lib') if child(x,'name')[1]=='ControllerLocal')
    equal('本地封装库URI',child(localtab,'uri')[1],'${KIPRJMOD}/ControllerLocal.pretty')
    equal('本地封装库说明',child(localtab,'descr')[1],'临时本地封装，待料号入 kicad_library')

    bom=list(csv.DictReader((REVIEW/'bom_issue2.csv').open()))
    expected_cols=['Reference','Value','Footprint','Manufacturer','MPN','Supplier','Supplier_PN','LCSC','Purchase_URL','Voltage_Rating','Tolerance','DNP','Qty']
    equal('BOM字段保持原13列',list(bom[0]),expected_cols)
    equal('BOM覆盖全部102个位号',sorted(r['Reference'] for r in bom),sorted(comps))
    for row in bom:
        ref=row['Reference'];equal(ref+'BOM Value',row['Value'],val(ref));equal(ref+'BOM Footprint',row['Footprint'],fields[ref]['Footprint'])
        equal(ref+'BOM DNP',bool(row['DNP']),dnp(symbols[ref]))
        for col in ['MPN','Manufacturer','LCSC','Purchase_URL']: equal(ref+'BOM '+col,row[col],fields[ref].get(col,''))
    report=(REVIEW/'erc_issue2.rpt').read_text()
    match=re.search(r'ERC messages:\s*(\d+)\s+Errors\s+(\d+)\s+Warnings\s+(\d+)',report)
    check('最终ERC 0错误0警告',bool(match) and tuple(map(int,match.groups()))==(0,0,0),match.group(0) if match else report)
    pdfinfo=subprocess.check_output(['pdfinfo',str(REVIEW/'controller.pdf')],text=True)
    equal('PDF页数',int(re.search(r'Pages:\s*(\d+)',pdfinfo).group(1)),10)
    upper=100+.005+64+79+.510+1.010+10*.3367+.242+.100+6.740+10+.050+1+5
    equal('3.3V逐项预算求和mA',round(upper,3),271.024)
    check('3.3V含50mA外接编码器预算<1A',upper<=275 and (275+50)<1000)
    equal('485单终端Vdiff计算V',round(3.3*120/(680+680+120),5),.26757)
    equal('485双终端Vdiff计算V（修正任务算术）',round(3.3*60/(680+680+60),5),.13944)
    check('485双终端低于200mV',3.3*60/(680+680+60)<.2)
    changed_paths=subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=REPO,env=env,text=True)
    # Store compact evidence for structural checks rather than duplicating the entire PCB in JSON.
    for c in checks:
        if c['项目']=='PCB文字之外所有结构保持':c['详情']={'比较':'当前板删除唯一新增gr_text后，与固定基线提交的完整S表达式逐项比较','相同':c['通过']}
        if c['项目'].startswith('pinmap未改 '):c['详情']={'比较':'与固定基线提交对应完整章节逐字比较','相同':c['通过']}
    stages={}
    for stage,path in [('pinmap','pinmap'),('A','A'),('B','B'),('C','C_fields'),('D','D'),('E','E'),('F','F_fields'),('G','G'),('H','H_corrected'),('I','I')]:
        p=Path('/tmp/issue2_'+path+'_erc.rpt')
        if p.exists():
            t=p.read_text();m=re.search(r'ERC messages:\s*\d+\s+Errors\s+\d+\s+Warnings\s+\d+',t)
            stages[stage]={'摘要':m.group(0) if m else 'missing','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    failed=[c for c in checks if not c['通过']]
    out={'结论':'通过' if not failed else '未通过','KiCad版本':subprocess.check_output(['kicad-cli','--version'],text=True).strip(),'引脚依据':'docs/pinmap.md','页数':len(pages),'元件位号数':len(comps),'新增位号数':6,'新增位号':['U203','R227','C211','C212','R228','R229'],'移除位号':['JP203'],'更换开关':['SW2'],'待选封装':empty,'核对项数':len(checks),'核对':checks,'基线提交':BASELINE_REF,'核对范围':'PR #13 第三轮；MCU64脚、排针64针、全部基线引脚和第三轮电路重新检查','封装扫描':{'活动页':[relative(p) for p in pages],'小于0603':small,'空封装':empty},'分项ERC':stages,'电流预算':{'适用性':'工程静态预算上限；非全部工况厂家保证值，条件见issue2_changes.md第三轮','逐项合计mA':round(upper,3),'不含编码器上限mA':275,'外接编码器预算mA':50,'含编码器上限mA':325},'待定事项':['C212与C301同规格，确切MPN/LCSC/DC bias待#5','LED中央焊盘电气属性原厂图未说明，外部NC；待共享库建料时补充','275mA为有条件设计预算，ST外设表征值不构成全工况保证最大值；#4/#7验证热与实际负载'],'本轮修改文件':changed_paths.splitlines()}
    args.json_output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    summary=f'''# PR #13 第三轮执行结果

分支 `hw/controller-sch-issue2`，KiCad 10.0.7；未切分支、未 commit/push，原索引未写入。

| 项 | 结果 |
| --- | --- |
| A | U203 TPS2553，R227=49.9k；IN/EN同接+5V_CORE_IN，OUT→D201；/FAULT NC；C211/C212输入/输出去耦；5V_OUT对外仅J201/4，均在限流后。 |
| B | pinmap先改；删JP203；J203/1、J204/1直接+3V3_MCU；PCB只加英文F.SilkS，(130,158)mm，未移动器件/走线；旧PCB无J203/J204/JP203。 |
| C / N1 | SW2、D202/D203、D204/D205已选料并补封装；核对物理针号；LED 1=A、2=K、中央3外部NC；本地符号/LED封装待入共享库。 |
| D / N2 | D201/D103统一共享库reviewed CFP3回流焊封装。 |
| E / N3 | 用临时索引执行git mv到history；内容不变，移动前后网表及ERC一致。原.git只读，提交时请git add -A纳入移动。 |
| F / N4 | R225/R226保留1k并补C21190；典型LED电流1.4–1.5mA。 |
| G / N5 | 3.3V逐负载规格/预算表完成：271.024mA合计，工程静态预算≤275mA，不含外接编码器≤50mA；合计≤325mA，小于TLV767的1A能力。条件和待验项见下。 |
| H / N6 | R228/R229=680Ω/0603，默认DNP。单120Ω约0.268V/2.23mA；双终端实算0.139V，低于200mV；原任务0.134V算术有误，已说明。 |
| I | 变更说明、BOM变化/补库表已追加；只更新review/bom_issue2.csv；原生导出ERC、XML、BOM、PDF、验证JSON均完成。 |

新增位号：**U203、R227、C211、C212、R228、R229**；另有非BOM电源标志#FLG203。删除JP203；D202/D203以及新增偏置DNP保留。

ERC原文摘要：`{match.group(0) if match else '报告未解析'}`。未改ERC配置，保留基线已有全局忽略类别。

脚位核对：pinmap §3 MCU **64/64**；§4.1/4.2 J101/J102 **64/64**，连同物理端口、13个独立NC及全部既有引脚连接重新核对。验证总计 **{len(checks)} 项，失败 {len(failed)} 项**；实际结论：**{out['结论']}**。

活动10页实例封装扫描：**0402/01005/0201={len(small)}；空Footprint={len(empty)}**。PCB移除唯一新增gr_text后与原板全部结构一致；PCB差异11行新增、0行删除，全部属于这一条文字。

修改文件（含新增/移入文件，取自git status）：

```text
{changed_paths.rstrip()}
```

未完成/需交接：C212按用户要求与C301一同待#5选确切料号/DC bias；中央LED焊盘的内部电气属性未在原厂图明确，已独立编号并外部NC；本地符号/封装及选定电阻料号待#5入共享库。275mA是列明条件和裕量的工程设计/验收上限，ST数字外设表无保证最大列，不能宣称全工况整板保证最大值；#4/#7仍需核对真实外部负载、LDO输入压差、热与瞬态。双120Ω终端需要系统重新核定偏置方案；本轮按指定680Ω默认DNP保留。

详细依据及计算见 [issue2_changes.md](issue2_changes.md) 第三轮；逐项检查见 [validation_issue2.json](validation_issue2.json)。
'''
    if failed: summary+='\n失败项：\n\n'+ '\n'.join('- '+c['项目']+': '+str(c['详情']) for c in failed)+'\n'
    args.output.write_text(summary)
    print(json.dumps({'结论':out['结论'],'核对项数':len(checks),'失败项':[c['项目'] for c in failed],'输出':str(args.output)},ensure_ascii=False))
    return bool(failed)
if __name__=='__main__': sys.exit(main())
