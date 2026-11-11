"""Partition one frozen native DRC into disjoint net-owned finish scopes."""
from pathlib import Path
import collections,hashlib,json,re

B=Path(__file__).resolve().parents[1];source=B/'review/pcb_drc.json'
d=json.loads(source.read_text(encoding='utf-8'));groups=collections.defaultdict(list);nets=collections.defaultdict(set)
power=re.compile(r'(^|/)(VBUS|[UVW]_PHASE|BR_SW|DC_FUSED|DC_INPUT_POS|[UVW]_SOURCE|[UVW]_GATE_[HL]|[UVW]_[HL]O|BR_GATE|[UVW]_BOOT|BB_L[12]|AUX_IN|AUX_FUSED|AUX_PROTECTED|\+12V_DRV|\+5V_INV|\+5V_SENSOR)$')
analog=re.compile(r'/Current sensing/|/Analog protection/|/Voltage and NTC/|^ADC_|^OC_(LOW|HIGH)_REF$|^OV_REF_|^TEMP_NTC$|^VREF_MCU$|^I_[UVW](_PORT)?$|^V_(DC|U|V|W)(_PORT)?$')
for entry in d['unconnected_items']:
    names=set(n for item in entry['items'] for n in re.findall(r'\[([^]]+)\]',item['description']))
    assert len(names)==1,names
    name=next(iter(names))
    group='ground' if name in ['GND','+3V3_INV'] else 'power' if power.search(name) or '/Auxiliary input/' in name or '/Driver supply/' in name else 'analog' if analog.search(name) else 'digital'
    groups[group].append(entry);nets[group].add(name)
manifest={'source_board_sha256':hashlib.sha256((B/'inverter.kicad_pcb').read_bytes()).hexdigest(),'source_drc_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scopes':{}}
for group,entries in groups.items():
    out=B/'review'/('compact_scope_'+group+'.json');subset=dict(d);subset['unconnected_items']=entries
    out.write_text(json.dumps(subset,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest['scopes'][group]={'gaps':len(entries),'nets':sorted(nets[group]),'drc':str(out)}
(B/'review/compact_finish_scope.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({k:len(v) for k,v in groups.items()},manifest['source_board_sha256'])
