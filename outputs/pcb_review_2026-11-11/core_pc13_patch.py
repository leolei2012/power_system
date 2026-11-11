"""Isolated PC13 escape proposal; does not edit the core owner's source board."""
from pathlib import Path
import json, shutil, math
import pcbnew as p

ROOT=Path(__file__).resolve().parents[2]
CORE=ROOT/'controller/hardware/g431_core'
OUT=Path(__file__).with_suffix('')
OUT.mkdir(exist_ok=True)
MM=p.FromMM
V=lambda q:p.VECTOR2I(MM(q[0]),MM(q[1]))
xy=lambda a:(round(p.ToMM(a.x),6),round(p.ToMM(a.y),6))
def load_clean():
    global b,fps,pcnet,gnet
    b=p.LoadBoard(str(OUT/'input_clean.kicad_pcb'))
    fps={f.GetReference():f for f in b.GetFootprints()}
    pcnet=next(a.GetNet() for a in fps['U30'].Pads() if a.GetNumber()=='2')
    gnet=next(a.GetNet() for a in fps['Y1'].Pads() if a.GetNumber()=='4')
load_clean()
remove={'c20b0854-5587-4750-9aa7-1f37c1b4b9a4',
        '4f28c86b-2b2b-41b6-98af-b5a10fd8ad92',
        '50c281e5-58a4-4396-8025-8b8a4358186b'}
assert not any(item.m_Uuid.AsString() in remove for item in b.GetTracks())

def obstacles(net):
    return [a for f in fps.values() for a in f.Pads() if a.GetNetCode()!=net.GetNetCode()]+[
            a for a in b.GetTracks() if a.GetNetCode()!=net.GetNetCode()]

def line(a,z,net,layer,width=.15):
    t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(z));t.SetWidth(MM(width));t.SetLayer(layer);t.SetNet(net)
    return t

def legal_line(a,z,net,layer,width=.15):
    if a==z:return True
    shape=line(a,z,net,layer,width).GetEffectiveShape(layer)
    return not any(o.IsOnLayer(layer) and shape.Collide(o.GetEffectiveShape(layer),MM(.15))
                   for o in obstacles(net))

def legal_via(q,net):
    return not any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(V(q),MM(.45))
                   for o in obstacles(net) for l in [p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu])

def add_path(points,net,layer,width=.15):
    for a,z in zip(points,points[1:]):
        if a!=z:b.Add(line(a,z,net,layer,width))

def add_via(q,net):
    v=p.PCB_VIA(b);v.SetPosition(V(q));v.SetWidth(MM(.6));v.SetDrill(MM(.3))
    v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(net);b.Add(v)

ground_start=(124.25,133.1);ground_end=(122.259,134.129)
solutions=[]
for x in [124.3,124.5,124.7,124.9,125.1,125.3]:
    for y in [133.6,133.8,134,134.2,134.4,134.6]:
        q=(x,y)
        if not legal_via(q,gnet):continue
        for fpath in [[ground_start,q],[ground_start,(x,133.1),q],[ground_start,(124.25,y),q]]:
            if not all(legal_line(a,z,gnet,p.F_Cu,.2) for a,z in zip(fpath,fpath[1:])):continue
            for back in [[q,ground_end],[q,(ground_end[0],y),ground_end],[q,(x,ground_end[1]),ground_end]]:
                if all(legal_line(a,z,gnet,p.B_Cu,.4) for a,z in zip(back,back[1:])):
                    solutions.append((q,fpath,back));break
            else:continue
            break
assert solutions,'No replacement crystal-ground via/return found'
solution=None
for q,fpath,back in solutions:
    added_before={a.m_Uuid.AsString() for a in b.GetTracks()}
    add_via(q,gnet);add_path(fpath,gnet,p.F_Cu,.2);add_path(back,gnet,p.B_Cu,.4)
    for x in [123.25,123.3,123.35,123.4,123.45]:
        for y in [134.6,134.8,135,135.2,135.4,135.6,135.8,136.0]:
            escape=[(122.25,133.25),(x,133.25),(x,y)]
            if not legal_via((x,y),pcnet):continue
            if not all(legal_line(a,z,pcnet,p.F_Cu) for a,z in zip(escape,escape[1:])):continue
            target=(131.27,138.89)
            for layer in [p.B_Cu,p.In2_Cu,p.F_Cu]:
                candidates=[[(x,y),target],[(x,y),(x,target[1]),target],[(x,y),(target[0],y),target]]
                for midx in [124,125,126,127,128,129,130,132,133,134]:
                    candidates.append([(x,y),(midx,y),(midx,target[1]),target])
                for midy in [134.5,135,135.5,136,136.5,137,137.5,138,139,140,141,142,143]:
                    candidates.append([(x,y),(x,midy),(target[0],midy),target])
                for route in candidates:
                    if all(legal_line(a,z,pcnet,layer) for a,z in zip(route,route[1:])):
                        solution={'remove_uuids':sorted(remove),'ground_via':q,'ground_F_path':fpath,
                                  'ground_B_path':back,'PC13_F_escape':escape,'PC13_route_layer':b.GetLayerName(layer),
                                  'PC13_route':route}
                        add_path(escape,pcnet,p.F_Cu);add_via((x,y),pcnet);add_path(route,pcnet,layer)
                        break
                if solution:break
            if solution:break
        if solution:break
    if solution:break
    load_clean()
assert solution,'Crystal ground can move, but no complete simple PC13 route found'
for name in ['controller.kicad_pro','fp-lib-table','sym-lib-table']:
    text=(CORE/name).read_text(encoding='utf-8-sig').replace('${KIPRJMOD}',CORE.as_posix())
    (OUT/name).write_text(text,encoding='utf-8')
p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
p.SaveBoard(str(OUT/'controller.kicad_pcb'),b)
solution['remaining_raw_unconnected']=b.GetConnectivity().GetUnconnectedCount(False)
(OUT/'proposal.json').write_text(json.dumps(solution,indent=2)+'\n',encoding='utf-8')
print(json.dumps(solution,indent=2),flush=True)
