"""Read-only independent check of the fine-geometry prototype."""
from pathlib import Path
from types import SimpleNamespace
import collections, hashlib, json, math, random, sys
B=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(B/'tools'))
import compact_fine_stitch as f
import compact_signal_rules as r
p=f.p
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source=B/'inverter.kicad_pcb'
seed=B/'review/compact_fine_smoke/inverter.kicad_pcb'
candidate=B/'review/compact_fine_smoke/stitch.work/inverter.kicad_pcb'
old=p.LoadBoard(str(seed));board=p.LoadBoard(str(candidate))
project=json.loads(candidate.with_suffix('.kicad_pro').read_text())
old_project=json.loads(source.with_suffix('.kicad_pro').read_text())
patch=json.loads((seed.parent/'stitch.json').read_text())
assert sha(source)==sha(seed)=='4d4f0c2ae1d5177ebf351e92cd70ae8483fde624233a5b98dc958461cede13fb'
assert sha(source.with_suffix('.kicad_pro'))=='6deb935ec5d0c9eb3f1ff1d00b76b9d00cdf18db3bc1566d2adb7fbcafd7554b'
old_items={a.m_Uuid.AsString():a for a in old.GetTracks()}
added=[a for a in board.GetTracks() if a.m_Uuid.AsString() not in old_items]
new_vias=[a for a in added if isinstance(a,p.PCB_VIA)]
assert len(new_vias)==2
assert all(abs(p.ToMM(a.GetWidth(p.F_Cu))-.5)<1e-9 and abs(p.ToMM(a.GetDrill())-.2)<1e-9 for a in new_vias)
assert all(a.IsOnLayer(p.F_Cu) and a.IsOnLayer(p.B_Cu) for a in new_vias)
assert all(abs(p.ToMM(a.GetWidth())-.125)<1e-9 for a in added if not isinstance(a,p.PCB_VIA))
assert all(a.GetNetname()=='SPI_A_SCK' for a in added)
new_geometry=f.original_geometry(board)
assert not [uid for uid,val in f.original_geometry(old).items() if new_geometry.get(uid)!=val]
assert candidate.with_suffix('.kicad_pro').read_bytes()==seed.with_suffix('.kicad_pro').read_bytes()
for c in old_project['net_settings']['classes']:
 assert c in project['net_settings']['classes']
for name,expected in [('VBUS',.4),('U_PHASE',.4),('/U half bridge/U_GATE_H',.2),('+12V_DRV',.2),('SPI_A_SCK',.15)]:
 assert r.clearance_for(name,project)==expected,(name,r.clearance_for(name,project))
for name in ['GND','+3V3_INV','VREF_MCU','VBUS','U_PHASE','V_SOURCE','/Encoders and SPI/ENC_B_VCC','/Voltage and NTC/V_DC_DIV','/Voltage and NTC/V_DC_DIV1','I_U_PORT','/U half bridge/U_HO']:
 assert not r.eligible(name),name
for name in ['SPI_A_SCK','MCU_ENABLE','ADC_I_U','ADC_V_DC','ADC_TEMP_NTC','FAULT_N']:
 assert r.eligible(name),name
assert all(r.fine_assigned(n,project) for n in ['SPI_A_SCK','MCU_ENABLE'])
g=f.Geometry(board,SimpleNamespace(),project)
code=next(n.GetNetCode() for n in board.GetNetsByNetcode().values() if n.GetNetname()=='SPI_A_SCK')
def oracle_via(at):
 copper=p.SHAPE_CIRCLE(f.V(*at),f.MM(.25));drill=p.SHAPE_CIRCLE(f.V(*at),f.MM(.1))
 if not g.inside(copper,.25):return False
 for ob in g.obstacles:
  if ob.code!=code and ob.kind!='track_keepout' and ob.shape.Collide(copper,f.MM(max(.15,ob.clearance))):return False
 for ob in g.protected:
  if ob.shape.Collide(copper,f.MM(max(.15,ob.clearance))):return False
 if any(ob.shape.Collide(copper,f.MM(.05)) for ob in g.surface_pads):return False
 if any(h.shape.Collide(drill,f.MM(g.hole_gap)) for h in g.holes):return False
 return True
def oracle_line(a,b,ly):
 shape=p.SHAPE_SEGMENT(f.V(*a),f.V(*b),f.MM(.125))
 if not g.inside(shape,.125/2):return False
 for ob in g.obstacles:
  if ly in ob.layers and ob.code!=code and ob.kind!='via_keepout' and ob.shape.Collide(shape,f.MM(max(.15,ob.clearance))):return False
 for h in g.holes:
  if h.code!=code and h.shape.Collide(shape,f.MM(g.hole_clear)):return False
 return True
rng=random.Random(431)
via_mismatch=[];line_mismatch=[]
for i in range(400):
 at=[rng.uniform(.6,59.4),rng.uniform(.6,59.4)]
 if g.via_ok(at,code,.15)!=oracle_via(at):via_mismatch.append(at)
 b=[max(.6,min(59.4,at[0]+rng.uniform(-1,1))),max(.6,min(59.4,at[1]+rng.uniform(-1,1)))]
 ly=rng.choice(g.layers)
 if g.line_ok(at,b,ly,code,.125,.15)!=oracle_line(at,b,ly):line_mismatch.append([at,b,ly])
assert not via_mismatch and not line_mismatch
f.GRID_GUARD=.002
blocked,vias=g.masks([1.,1.,59.,59.],.2,code,.125,.15)
free_via_grid=0;free_line_grid=0
for i in range(1200):
 y=rng.randrange(vias.shape[0]);x=rng.randrange(vias.shape[1]);at=[1+x*.2,1+y*.2]
 if not vias[y,x]:
  free_via_grid+=1;assert oracle_via(at),('via mask false negative',at)
 z=rng.randrange(len(g.layers))
 if not blocked[z,y,x]:
  free_line_grid+=1;assert oracle_line(at,at,g.layers[z]),('line mask false negative',at)
assert free_via_grid and free_line_grid
drc_file=candidate.parent/'final_drc.json';fixed_file=candidate.parent/'final_fixed.json'
drc=json.loads(drc_file.read_text());fixed=json.loads(fixed_file.read_text())
errors=[e for e in drc['violations'] if e['severity']=='error']
assert not errors and fixed['pass']
assert len(patch['accepted'])==1 and patch['validation']['after_unconnected']==214
assert patch['validation']['actual_remaining_error_count']==0
summary={'pass':True,'purpose':'Prototype only; private project rules changed. Not mergeable into old 4d4f baseline.',
 'candidate':str(candidate),'candidate_sha256':sha(candidate),'main_source_unchanged':sha(source)==sha(seed),
 'main_project_unchanged':sha(source.with_suffix('.kicad_pro'))=='6deb935ec5d0c9eb3f1ff1d00b76b9d00cdf18db3bc1566d2adb7fbcafd7554b',
 'main_original_classes_and_clearances_preserved':True,'default_preferred':'.15/.6/.3','fine_preferred':'.125/.5/.2',
 'true_min_clearance':.15,'via_copper_radius':.25,'via_drill_radius':.1,'annular_width':.15,
 'all_original_geometry_preserved':True,'closed_net':'SPI_A_SCK','global_gaps_before':215,'global_gaps_after':214,
 'actual_added_vias':len(new_vias),'actual_added_segments':len(added)-len(new_vias),
 'native_exact_oracle_vias_tested':400,'native_exact_oracle_lines_tested':400,
 'native_exact_oracle_mismatches':0,'sampled_grid_points':1200,'via_grid_free_points_verified':free_via_grid,'line_grid_free_points_verified':free_line_grid,
 'electrical_errors':len(errors),'listed_airwires':len(drc['unconnected_items']),
 'warning_types':dict(collections.Counter(e['type'] for e in drc['violations'] if e['severity']=='warning')),
 'fixed_kelvin_pass':fixed['pass'],'fixed_summary':fixed['summary'],'drc':str(drc_file),'fixed':str(fixed_file)}
(seed.parent/'prototype_validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
