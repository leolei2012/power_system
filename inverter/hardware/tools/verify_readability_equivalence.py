"""Check every original physical pin/net and symbol property after graphical redraw."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import sexpdata as sx

B=Path(__file__).resolve().parents[1]
snapshot=B.parent/'history/rev_b_before_readability_2026-11-06.zip'
z=ZipFile(snapshot)
old=ET.fromstring(z.read('hardware/review/inverter.net.xml'))
new=ET.parse(B/'review/inverter.net.xml').getroot()
candidate_path=B/'tools/pcb_footprint_candidates.json'
candidate_map=json.loads(candidate_path.read_text(encoding='utf-8'))['footprint_map'] if candidate_path.exists() else {}
footprint_changes={}
FILTER_FIELD='ki_fp_filters'

def is_tag(x,name):return isinstance(x,list) and x and str(x[0])==name

def children(data,name):return [v for v in data if is_tag(v,name)]

def props(data):return {v[1]:v[2] for v in children(data,'property')}

# Compare embedded-library defaults themselves; omit only exact redundant
# instance copies.  Per-instance overrides remain in the strict comparison.
native_pages={};old_defaults={};new_defaults={};filter_cleanups=[]
for path in B.glob('*.kicad_sch'):
    source=sx.loads(z.read('hardware/'+path.name).decode('utf-8-sig'))
    target=sx.loads(path.read_text(encoding='utf-8-sig'))
    native_pages[path.name]=(source,target)
    page_fields=[]
    for data,defaults in [(source,old_defaults),(target,new_defaults)]:
        embedded=next(v for v in data if is_tag(v,'lib_symbols'))
        libraries={v[1]:v for v in children(embedded,'symbol')}
        units={}
        for instance in children(data,'symbol'):
            fields=props(instance);ref=fields['Reference']
            if ref.startswith('#'):continue
            libid=next(v[1] for v in instance if is_tag(v,'lib_id'))
            unit=next(v[1] for v in instance if is_tag(v,'unit'))
            default=props(libraries[libid]).get(FILTER_FIELD)
            if ref in defaults:assert defaults[ref]==default,(ref,'inconsistent embedded library filters')
            defaults[ref]=default
            units[ref,unit]=fields
        page_fields.append(units)
    for key,fields in page_fields[0].items():
        after_fields=page_fields[1].get(key,{})
        if FILTER_FIELD in fields and FILTER_FIELD not in after_fields:
            assert fields[FILTER_FIELD]==old_defaults[key[0]],(path.name,key,'non-default filter removed')
            filter_cleanups.append({'sheet':path.name,'reference':key[0],'unit':key[1],'retained_library_filter':fields[FILTER_FIELD]})
assert old_defaults==new_defaults,'Embedded physical-symbol footprint filters changed'

def omit_redundant_filter(fields,ref,defaults):
    fields=dict(fields)
    if defaults.get(ref) is not None and fields.get(FILTER_FIELD)==defaults[ref]:fields.pop(FILTER_FIELD,None)
    return fields
def components(t):return {c.attrib['ref']:c for c in t.findall('./components/comp')}
def nets(t):
    pins={};groups=set()
    for net in t.findall('./nets/net'):
        nodes=frozenset((n.attrib['ref'],n.attrib['pin']) for n in net.findall('node') if not n.attrib['ref'].startswith('#'))
        if not nodes:continue
        groups.add(nodes)
        for key in nodes:pins[key]=net.attrib['name'].rsplit('/',1)[-1]
    return pins,groups
oc,nc=components(old),components(new)
assert set(oc)==set(nc),('physical component set changed',set(oc)^set(nc))
for ref in oc:
    for key in ['value','footprint','datasheet']:
        a,b=oc[ref].findtext(key),nc[ref].findtext(key)
        if key=='footprint' and a!=b:
            assert not a and candidate_map.get(ref)==b,(ref,'unexpected footprint change',a,b)
            footprint_changes[ref]=b
        else:assert a==b,(ref,key)
    a=omit_redundant_filter({p.attrib['name']:p.text for p in oc[ref].findall('./fields/field')},ref,old_defaults)
    b=omit_redundant_filter({p.attrib['name']:p.text for p in nc[ref].findall('./fields/field')},ref,new_defaults)
    if ref in footprint_changes:a.pop('Footprint',None);b.pop('Footprint',None)
    assert a==b,(ref,'fields differ')
    a=omit_redundant_filter({p.attrib['name']:p.attrib.get('value') for p in oc[ref].findall('property')},ref,old_defaults)
    b=omit_redundant_filter({p.attrib['name']:p.attrib.get('value') for p in nc[ref].findall('property')},ref,new_defaults)
    # Sheetfile/Sheetname are metadata; the physical part and DNP must not change.
    for key in ['Sheetfile','Sheetname']:a.pop(key,None);b.pop(key,None)
    assert a==b,(ref,'DNP or component property differs')
op,og=nets(old);np,ng=nets(new)
assert set(op)==set(np),('physical pin set changed',set(op)^set(np))
for key in op:
    if op[key].startswith('unconnected-'):
        assert np[key].startswith('unconnected-'),(key,op[key],np[key])
    else:assert op[key]==np[key],(key,op[key],np[key])
assert og==ng,('net membership changed',len(og-ng),len(ng-og))
def stats(data):return Counter(str(v[0]) for v in data if isinstance(v,list) and v)
before=Counter();after=Counter()
for path in B.glob('*.kicad_sch'):
    source,target=native_pages[path.name]
    before+=stats(source);after+=stats(target)
    def symbols(data):
        result={}
        for s in data:
            if not is_tag(s,'symbol'):continue
            pp={p[1]:p[2] for p in s if is_tag(p,'property')}
            ref=pp['Reference']
            if ref.startswith('#'):continue
            unit=next(p[1] for p in s if is_tag(p,'unit'))
            lib=next(p[1] for p in s if is_tag(p,'lib_id'))
            if ref in footprint_changes:pp.pop('Footprint',None)
            pp=omit_redundant_filter(pp,ref,old_defaults)
            result[ref,unit]=(lib,pp,old_defaults[ref])
        return result
    assert symbols(source)==symbols(target),(path.name,'physical symbol/unit metadata differs')
report={'result':'PASS','scope':'Every physical pin connectivity, value and DNP unchanged; only recorded empty-to-candidate footprints and exact redundant instance-filter cleanup are allowed.',
        'physical_components':len(oc),'physical_pins':len(op),'net_groups':len(og),'sheets':18,
        'before':{k:before[k] for k in ['wire','global_label','label']},
        'after':{k:after[k] for k in ['wire','global_label','label']},
        'footprint_candidates_assigned':footprint_changes,
        'redundant_instance_metadata_cleanup':{
            'field':FILTER_FIELD,'removed_symbol_unit_fields':len(filter_cleanups),
            'affected_physical_references':len({entry['reference'] for entry in filter_cleanups}),
            'counts_by_sheet':dict(Counter(entry['sheet'] for entry in filter_cleanups)),
            'reason':'KiCad 10 drops reserved ki_fp_filters user fields when loading PCB footprints; redundant copies cause schematic/PCB parity warnings.',
            'comparison_rule':'Only an instance value exactly matching its embedded-library default is omitted; overrides and all other metadata remain strict.',
            'embedded_library_filters_unchanged':old_defaults==new_defaults,
            'cleanup_script':'tools/cleanup_instance_fp_filters.py',
            'cleanup_report':'review/symbol_filter_cleanup.json'},
        'snapshot':str(snapshot.relative_to(B.parent)),
        'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        'notes':['KiCad-scoped local names normalized only for name comparison; complete physical node group sets are also compared exactly.',
                 'Standard power/ground symbols and one VBUS ERC power flag are graphical/electrical declarations, not BOM additions.',
                 'No component values, DNP choices or electrical design changed; any footprint assignments are listed explicitly above.',
                 'Redundant instance ki_fp_filters cleanup is counted separately; embedded library filters remain unchanged.']}
(B/'review/readability_equivalence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'review/readability_equivalence.txt').write_text('PASS\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
