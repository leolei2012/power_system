"""Publish a validated routing checkpoint as a review board, not fabrication."""
from pathlib import Path
import argparse,collections,hashlib,json,shutil
import pcbnew as p
from compact_route import fixed_geometry
from compact_power_copper import audit_power_connectivity
from compact_verify_fixed import outlines
B=Path(__file__).resolve().parents[1];R=B/'review/pcb_rev_e_2026-11-11'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--drc',type=Path,required=True)
    ap.add_argument('--physical-review',type=Path,required=True);ap.add_argument('--kelvin-review',type=Path,required=True)
    a=ap.parse_args();a.candidate=a.candidate.resolve();assert a.candidate!=(B/'inverter.kicad_pcb').resolve()
    native=json.loads(a.drc.read_text(encoding='utf-8'));errors=[v for v in native['violations'] if v['severity']=='error'];assert not errors,errors
    physical=json.loads(a.physical_review.read_text(encoding='utf-8'));assert physical['mapping_pass'] and physical['mating']['pass']
    inv=physical['boards']['inverter'];assert not inv['errors'];assert inv['input_sha256']['board']==sha(a.candidate),('Stale physical review',inv['input_sha256'])
    kelvin=json.loads(a.kelvin_review.read_text(encoding='utf-8'));assert kelvin['pass'];assert kelvin['source_sha256_after']==sha(a.candidate),'Stale Kelvin review'
    board=p.LoadBoard(str(a.candidate));old=p.LoadBoard(str(B/'inverter.kicad_pcb'))
    assert fixed_geometry(board)==fixed_geometry(old),'Critical locked track/via changed'
    current_zones={z.m_Uuid.AsString():z for z in board.Zones()}
    for z in old.Zones():
        other=current_zones[z.m_Uuid.AsString()]
        assert (z.GetNetname(),list(z.GetLayerSet().Seq()),z.GetIsRuleArea(),outlines(z.Outline()))==(other.GetNetname(),list(other.GetLayerSet().Seq()),other.GetIsRuleArea(),outlines(other.Outline())),('Original zone geometry changed',z.GetZoneName())
    rec=json.loads((R/'power/power_copper.json').read_text(encoding='utf-8'));geometry=audit_power_connectivity(board,rec);geometry['pass']=True
    board.BuildConnectivity();raw=board.GetConnectivity().GetUnconnectedCount(False)
    tracks=[t for t in board.GetTracks() if not isinstance(t,p.PCB_VIA)];vias=[t for t in board.GetTracks() if isinstance(t,p.PCB_VIA)]
    previous=json.loads((R/'pcb_review.json').read_text(encoding='utf-8'));previous.update(
        status='Rev E PCB0.1 review; ordinary, driver and auxiliary routing still incomplete',
        tracks=len(tracks),vias=len(vias),zones=sum(not z.GetIsRuleArea() for z in board.Zones()),
        actual_DRC_electrical_geometry_errors=0,
        actual_DRC_warning_types=dict(collections.Counter(v['type'] for v in native['violations'] if v['severity']=='warning')),
        actual_DRC_unconnected_items_reported=len(native['unconnected_items']),raw_connectivity_unconnected_count=raw,
        critical_power_geometry=geometry,routing_candidate=str(a.candidate),routing_candidate_sha256=sha(a.candidate),
        native_DRC=str(a.drc.resolve()),native_DRC_sha256=sha(a.drc),physical_review=str(a.physical_review.resolve()),
        kelvin_review=str(a.kelvin_review.resolve()),manufacturing_release=False,
        routing_note='Locked critical 277 tracks/98 vias preserved. Added ordinary routes, separate GND stitches, and quiet In3 3V3_INV pour limited to x<=142.5 mm. VBUS sheet priority2 takes precedence over logic priority1; 19 ordinary In3 tracks withdrawn to preserve all14 physical power groups. Full routing/functional loops remain unfinished.')
    previous.pop('unresolved_local_route_attempts',None)
    OUT=B/'inverter.kicad_pcb';backup=R/'before_remaining_routes_inverter.kicad_pcb'
    if not backup.exists():shutil.copyfile(OUT,backup);shutil.copyfile(OUT.with_suffix('.kicad_pro'),backup.with_suffix('.kicad_pro'))
    shutil.copyfile(a.candidate,OUT);shutil.copyfile(a.candidate.with_suffix('.kicad_pro'),OUT.with_suffix('.kicad_pro'))
    previous['board_sha256']=sha(OUT);previous['published_board']=str(OUT)
    (R/'pcb_review.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    geometry.update(board_sha256=sha(OUT));(R/'critical_geometry_check.json').write_text(json.dumps(geometry,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:previous[k] for k in ['tracks','vias','zones','raw_connectivity_unconnected_count','actual_DRC_warning_types','board_sha256']},indent=2))
if __name__=='__main__':main()
