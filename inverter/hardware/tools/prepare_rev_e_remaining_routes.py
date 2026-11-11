"""Export a conservative DSN for ordinary routes; never saves the native PCB.

Masks are represented by larger temporary pad obstacles, the routing boundary
has an extra edge margin, and Kelvin copper is protected by DSN-only keepouts.
"""
from pathlib import Path
import argparse,hashlib,json,math,re
import pcbnew as p
from compact_route import fixed_geometry

B=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--boundary-inset',type=float,default=.4)
    args=ap.parse_args();source_hash=hashlib.sha256(args.board.read_bytes()).hexdigest()
    board=p.LoadBoard(str(args.board));locked=fixed_geometry(board);mask_changes=[]
    for fp in board.GetFootprints():
        pp=list(fp.Pads())
        for pad in pp:
            if not pad.GetNumber() or not (pad.IsOnLayer(p.F_Cu) or pad.IsOnLayer(p.B_Cu)):continue
            opening=next((a for a in pp if not a.GetNumber() and not a.IsOnLayer(p.F_Cu)
                          and not a.IsOnLayer(p.B_Cu) and (a.IsOnLayer(p.F_Mask) or a.IsOnLayer(p.B_Mask))
                          and a.GetPosition()==pad.GetPosition()),None)
            if opening is None:continue
            old=pad.GetSize();size=opening.GetSize()
            if size.x>old.x or size.y>old.y:
                pad.SetSize(p.VECTOR2I(max(old.x,size.x),max(old.y,size.y)))
                mask_changes.append(fp.GetReference()+'.'+pad.GetNumber())
    raw=args.output.with_suffix('.raw.dsn');assert p.ExportSpecctraDSN(board,str(raw))
    assert fixed_geometry(board)==locked,'Export modified fixed copper identity'
    text=raw.read_text(encoding='utf-8')
    for layer in ['In1.Cu','In4.Cu']:
        text=re.sub(r'(\(layer '+re.escape(layer)+r'\s+\(type )power(\))',r'\1signal\2',text,count=1)
    lo=round((100+args.boundary_inset)*1000);hi=round((160-args.boundary_inset)*1000)
    boundary=f'(boundary (path pcb 0 {hi} -{hi} {lo} -{hi} {lo} -{lo} {hi} -{lo} {hi} -{hi}))'
    text,n=re.subn(r'\(boundary\s+\(path pcb 0\s+.*?\)\s*\)',boundary,text,count=1,flags=re.S)
    assert n==1
    rec=json.loads((B/'review/pcb_rev_e_2026-11-11/power/power_copper.json').read_text(encoding='utf-8'))
    protected=set(rec['protected_kelvin_uuids']);guards=[]
    def polygon(name,layer,pts):
        coords='  '.join(str(round(x*1000))+' '+str(round(-y*1000)) for x,y in pts+[pts[0]])
        guards.append('    (keepout "'+name+'" (polygon '+layer+' 0  '+coords+'))\n')
    for item in rec['tracks']:
        if item['uuid'] not in protected:continue
        a,c=item['a'],item['b'];dx,dy=c[0]-a[0],c[1]-a[1];length=math.hypot(dx,dy)
        if not length:continue
        h=.35;nx,ny=-dy/length*h,dx/length*h;ux,uy=dx/length*h,dy/length*h
        polygon('Kelvin_'+item['uuid'],item['layer'],[(a[0]-ux+nx,a[1]-uy+ny),(c[0]+ux+nx,c[1]+uy+ny),(c[0]+ux-nx,c[1]+uy-ny),(a[0]-ux-nx,a[1]-uy-ny)])
    for item in rec['vias']:
        if item['uuid'] not in protected:continue
        x,y=item['xy'];pts=[(x+.55*math.cos(i*math.pi/8),y+.55*math.sin(i*math.pi/8)) for i in range(16)]
        for layer in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']:polygon('KelvinVia_'+item['uuid'],layer,pts)
    for fp in board.GetFootprints():
        if fp.GetReference() not in ['U10','U11','U12']:continue
        for pad in fp.Pads():
            if pad.GetNumber() not in ['1','8']:continue
            bb=pad.GetBoundingBox();x0,y0=p.ToMM(bb.GetX())-.25,p.ToMM(bb.GetY())-.25;x1,y1=p.ToMM(bb.GetRight())+.25,p.ToMM(bb.GetBottom())+.25
            polygon('KelvinPad_'+fp.GetReference()+'_'+pad.GetNumber(),fp.GetLayerName(),[(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
    # Ordinary tracks and via antipads can sever a sheet without touching a
    # locked track. Reserve its actual contour, then audit saved fill on import.
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname()!='VBUS' or not z.IsOnLayer(p.In3_Cu):continue
        for i in range(z.Outline().OutlineCount()):
            contour=z.Outline().COutline(i)
            polygon('MainPowerPlane_'+z.m_Uuid.AsString()+'_'+str(i),'In3.Cu',[(p.ToMM(contour.CPoint(j).x),p.ToMM(contour.CPoint(j).y)) for j in range(contour.PointCount())])
    text=text.replace('(boundary',''.join(guards)+'    (boundary',1)
    args.output.write_text(text,encoding='utf-8')
    assert hashlib.sha256(args.board.read_bytes()).hexdigest()==source_hash
    args.output.with_suffix('.guards.json').write_text(json.dumps({'native_board_sha256':source_hash,'Kelvin_keepouts':len(guards),'mask_obstacles_enlarged':mask_changes,'native_source_unchanged':True,'boundary_inset_mm':args.boundary_inset},indent=2)+'\n',encoding='utf-8')
    print('Exported guarded DSN; mask obstacles',len(mask_changes),'Kelvin guards',len(guards),flush=True)


if __name__=='__main__':main()
