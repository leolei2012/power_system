"""Audit/publish the first Rev E PCB review; no production package generation."""
from pathlib import Path
import collections,hashlib,json,shutil,xml.etree.ElementTree as ET
import pcbnew as p
from compact_power_copper import audit_power_connectivity

B=Path(__file__).resolve().parents[1];R=B/'review/pcb_rev_e_2026-11-11';S=R/'power/inverter.kicad_pcb';OUT=B/'inverter.kicad_pcb'


def main():
 report=json.loads((R/'power/power_copper.json').read_text(encoding='utf-8'))
 drc=json.loads((R/'power/power_drc.json').read_text(encoding='utf-8'))
 errors=[v for v in drc['violations'] if v['severity']=='error'];assert not errors,errors
 board=p.LoadBoard(str(S));fps={f.GetReference():f for f in board.GetFootprints()};xml=ET.parse(B/'review/inverter.net.xml').getroot();cm={c.attrib['ref']:c for c in xml.findall('./components/comp')}
 assert set(fps)==set(cm)|{'H1','H2','H3','H4'}
 nm={(a.attrib['ref'],a.attrib['pin']):n.attrib['name'] for n in xml.findall('./nets/net') for a in n.findall('node')}
 actual={};named_pad_count=0
 for ref,c in cm.items():
  f=fps[ref];assert f.GetFPIDAsString()==c.findtext('footprint'),ref;assert f.GetValue()==c.findtext('value'),ref
  assert f.IsDNP()==(c.find("./property[@name='dnp']") is not None),ref
  for pad in f.Pads():
   if not pad.GetNumber():continue
   key=(ref,pad.GetNumber());normal=pad.GetNetname().replace('{slash}','/');assert nm[key]==normal,(key,nm[key],normal);actual[key]=normal;named_pad_count+=1
 assert actual==nm
 items={a.m_Uuid.AsString():a for a in list(board.GetTracks())+list(board.Zones())}
 expected=report['tracks']+report['vias']+[z for z in report['zones'] if not z.get('keepout')]
 for e in expected:assert e['uuid'] in items and items[e['uuid']].GetNetname()==e['net'],e
 try:geometry=audit_power_connectivity(board,report)
 except AssertionError as error:geometry={'pass':False,'incomplete':str(error)}
 else:geometry['pass']=True
 (R/'critical_geometry_check.json').write_text(json.dumps(geometry,indent=2),encoding='utf-8')
 assert geometry['pass'],geometry
 bank_counts=collections.Counter(v['purpose'] for v in report['vias'] if 'four-via bank' in v['purpose'])
 unresolved=[v for v in report['failed'] if not v.get('resolved_by_local_route')]
 board.BuildConnectivity();raw=board.GetConnectivity().GetUnconnectedCount(False)
 summary={'status':'Rev E PCB0.1 layout/main-power and Kelvin review; driver, auxiliary and ordinary signal routing incomplete',
          'source_XML_sha256':hashlib.sha256((B/'review/inverter.net.xml').read_bytes()).hexdigest(),
          'schematic_components':317,'DNP':sum(fps[r].IsDNP() for r in cm),'mechanical_holes':4,
          'physical_pin_keys':len(actual),'named_copper_pads_including_repeated_tab':named_pad_count,
          'pad_net_FP_value_DNP_parity':'PASS','size_mm':[60,60],'layers':6,'thickness_candidate_mm':1.6,
          'tracks':len(report['tracks']),'vias':len(report['vias']),'zones':sum(not z.get('keepout') for z in report['zones']),
          'actual_DRC_electrical_geometry_errors':len(errors),'actual_DRC_warning_types':dict(collections.Counter(v['type'] for v in drc['violations'] if v['severity']=='warning')),
          'actual_DRC_unconnected_items_reported':len(drc['unconnected_items']),'raw_connectivity_unconnected_count':raw,
          'critical_power_geometry':geometry,'actual_four_via_bank_counts':dict(bank_counts),
          'unresolved_local_route_attempts':unresolved,
          'assembly_limits':['Shunt ground return uses four0.8/0.4mm vias in each ground-side pad; fill/cap or solder-wicking review required before fabrication.',
                             'Gate and auxiliary bootstrap layer changes may use vias near or on SMD pads; assembly remains unqualified.',
                             'MOS Q1-Q7 shared footprints intentionally have no3D model; rendered exposed pads are not missing-path failures.',
                             'Copper thickness, thermal/current rating, switching overshoot, insertion height and button access require subsequent validation.']}
 if OUT.exists():
  backup=R/'previous_published_inverter.kicad_pcb';shutil.copyfile(OUT,backup)
 shutil.copyfile(S,OUT);shutil.copyfile(S.with_suffix('.kicad_pro'),B/'inverter.kicad_pro')
 summary['published_board']=str(OUT);summary['board_sha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
 (R/'pcb_review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 report['candidate_sha256']=hashlib.sha256(S.read_bytes()).hexdigest();report['published_sha256']=summary['board_sha256'];report['connectivity_audit']=geometry
 (R/'power/power_copper.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in summary.items() if k not in ['unresolved_local_route_attempts','critical_power_geometry','actual_four_via_bank_counts','assembly_limits']},indent=2))
 print('Power geometry:',geometry.get('pass'),geometry.get('incomplete',''));print('Bank counts',dict(bank_counts))


if __name__=='__main__':main()
