"""Compare compact revision wiring against the immutable routed PCB0.1 XML."""
from pathlib import Path
from zipfile import ZipFile
import collections
import hashlib
import json
import xml.etree.ElementTree as ET

B=Path(__file__).resolve().parents[1]
archive=B.parent/'history/pcb_0_1_200x140_before_60mm_2026-11-06.zip'
old=ET.fromstring(ZipFile(archive).read('inverter/hardware/review/inverter.net.xml'))
new=ET.parse(B/'review/inverter.net.xml').getroot()
contract=json.loads((B/'tools/compact_design.json').read_text(encoding='utf-8'))
oldc={x.attrib['ref']:x for x in old.findall('./components/comp')}
newc={x.attrib['ref']:x for x in new.findall('./components/comp')}
assert set(oldc)==set(newc) and len(newc)==313,'component reference set changed'

def fields(c):return {x.attrib['name']:x.text or '' for x in c.findall('./fields/field')}
def dnp(c):return any(x.attrib.get('name')=='dnp' for x in c.findall('property'))
def terminal(ref,pin,modern):
    if modern and ref in ['Q1','Q2','Q3','Q4','Q5','Q6','Q7']:
        pin=int(pin)
        return str(1 if pin==4 else 2 if pin in [5,6,7,8] else 3 if pin in [1,2,3] else -1)
    return pin

def networks(tree,modern):
    result={};physical={}
    for n in tree.findall('./nets/net'):
        points=set()
        for x in n.findall('node'):
            key=x.attrib['ref'],x.attrib['pin'];assert key not in physical
            physical[key]=n.attrib['name']
            points.add((key[0],terminal(*key,modern)))
        result[n.attrib['name']]=points
    return result,physical

a,ap=networks(old,False);b,bp=networks(new,True)
assert a==b,{'missing_or_changed':[(n,sorted(a.get(n,set())-b.get(n,set())),sorted(b.get(n,set())-a.get(n,set()))) for n in a.keys()|b.keys() if a.get(n)!=b.get(n)]}
for ref in ['Q1','Q2','Q3','Q4','Q5','Q6','Q7']:
    assert {p for r,p in bp if r==ref}==set(map(str,range(1,9)))
    for terminal_name,pins in contract['mos_pin_contract'].items():
        assert len({bp[ref,str(pin)] for pin in pins})==1,(ref,terminal_name,'split internal terminal')
    assert newc[ref].findtext('value')=='BSC110N15NS5'

changed=[]
for ref,c in newc.items():
    before=oldc[ref];allowed=contract['changes'].get(ref,{})
    for tag,key in [('value','Value'),('footprint','Footprint')]:
        expected=allowed.get(key,before.findtext(tag) or '')
        assert (c.findtext(tag) or '')==expected,(ref,key,c.findtext(tag),expected)
    expected_dnp=contract.get('DNP_changes',{}).get(ref,{}).get('to',dnp(before))
    assert dnp(c)==expected_dnp,(ref,'unexpected DNP change')
    for key,value in allowed.items():
        if key in ['before_fields','Value','Footprint']:continue
        assert fields(c).get(key)==value,(ref,key,'metadata mismatch')
    if allowed:changed.append(ref)

report={'status':'PASS','reference_count':len(newc),'old_physical_pins':len(ap),'new_physical_pins':len(bp),
        'netgroups':len(a),'all_original_functional_terminals_and_netgroups_equal':True,
        'physical_expansion':'Seven MOS devices explicitly changed from G1/D2/S3 to S1,2,3/G4/D5,6,7,8',
        'DNP_exception':contract['DNP_changes'],'changed_component_metadata_or_footprint_refs':sorted(changed),
        'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'new_xml_sha256':hashlib.sha256((B/'review/inverter.net.xml').read_bytes()).hexdigest(),
        'scope':'Static connectivity and explicit component migration only; no thermal/switching/prototype approval'}
for suffix in ['json','txt']:(B/('review/compact_equivalence.'+suffix)).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS:',len(newc),'references;',len(ap),'->',len(bp),'physical pins;',len(a),'unchanged functional netgroups')
