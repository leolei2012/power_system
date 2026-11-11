import pcbnew as p,json,math,itertools,hashlib
from pathlib import Path
B=Path(__file__).resolve().parents[1]
file=B/'tools/compact_control_placement.json';d=json.loads(file.read_text());b=p.LoadBoard(str(B/'review/compact_work/inverter.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
for r,w in d['placements'].items():
 f=fps[r]
 if f.IsFlipped()!=(w['side']=='B'):f.Flip(f.GetPosition(),False)
 f.SetOrientationDegrees(w['rotation_deg']);f.SetPosition(p.VECTOR2I(round(w['x']*1e6),round(w['y']*1e6)))
def dst(a,b):return math.hypot(p.ToMM(a.GetPosition().x-b.GetPosition().x),p.ToMM(a.GetPosition().y-b.GetPosition().y))
report={'ADC':{},'decoupling':{}}
for i in range(69,77):
 r='C'+str(i);pairs=[(dst(a,v),a,v)for a in fps[r].Pads() for v in fps['U30'].Pads() if a.GetNetname()==v.GetNetname() and a.GetNetname() not in ['GND','+3V3']]
 z=min(pairs,key=lambda z:z[0]);report['ADC'][r]={'net':z[1].GetNetname(),'MCU_pin':z[2].GetNumber(),'distance_mm':round(z[0],3)}
for i,u in [(63,'U30'),(64,'U30'),(65,'U30'),(66,'U30'),(67,'U30'),(77,'U30'),(79,'U30'),(56,'U22'),(57,'U23'),(58,'U24'),(59,'U25'),(60,'U26'),(61,'U27'),(62,'U28')]:
 r='C'+str(i);pairs=[(dst(a,v),a,v)for a in fps[r].Pads() for v in fps[u].Pads() if a.GetNetname()==v.GetNetname() and a.GetNetname()!='GND']
 if pairs:
  z=min(pairs,key=lambda z:z[0]);report['decoupling'][r]={'device':u,'net':z[1].GetNetname(),'pin':z[2].GetNumber(),'distance_mm':round(z[0],3)}
coll=[]
for (r,a),(s,c) in itertools.combinations(d['placements'].items(),2):
 if a['side']!=c['side']:continue
 x=a['courtyard_bbox_mm'];y=c['courtyard_bbox_mm']
 if x[0]<y[2] and x[2]>y[0] and x[1]<y[3] and x[3]>y[1]:coll.append([r,s])
report['same_side_courtyard_overlap']=coll
report['coverage']={'owned_count':len(d['owned_refs']),'placed_count':len(d['placements']),'missing':sorted(set(d['owned_refs'])-set(d['placements'])),'extra':sorted(set(d['placements'])-set(d['owned_refs']))}
report['note']='Pad distances are actual selected same-net pad centres after the exact Flip-then-rotate import convention. Geometric placement result only; no traces, signal integrity, thermal, DRC or manufacture approval is implied.'
report['source_work_board_sha256']=hashlib.sha256((B/'review/compact_work/inverter.kicad_pcb').read_bytes()).hexdigest()
report['power_placement_sha256']=hashlib.sha256((B/'tools/compact_power_placement.json').read_bytes()).hexdigest()
(B/'review/compact_control_pad_audit.json').write_text(json.dumps(report,indent=2)+'\n')
d['validation']['actual_pad_audit']=report
d['validation']['source_power_placement_sha256']=report['power_placement_sha256']
d['notes'].append('C59/C60 use local B-side placement across a supply/ground via pair rather than long F-side loops;100n pad-to-VCC distances are2.23/3.07mm. Keep direct local via return during routing. MCU C64 improved by turning its supply pad toward pin32.')
file.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,indent=2))
