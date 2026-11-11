"""Find short, exact-native-checked F-layer escapes to legal 0.6/0.3 vias.

Uses the existing standalone geometry/mask library, never any old PCB builder.
All mutations are confined to an explicitly supplied current-core candidate.
"""
from pathlib import Path
import argparse,heapq,json,math,sys,types
import pcbnew as p

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[2]
sys.path.insert(0,str(REPO/'inverter/hardware/tools'))
import compact_fast_stitch as fast
s=fast.s
fast.GRID_GUARD=.002


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--pin',action='append',help='Repeatable MCU physical pad; default the five crowded GPIO pads.')
    ap.add_argument('--via-box',nargs=4,type=float,metavar=('X0','Y0','X1','Y1'),help='Optional local via goal rectangle to leave adjacent-pin escape room.')
    args=ap.parse_args();board_path=args.board.resolve();pro=board_path.with_suffix('.kicad_pro');blob=pro.read_bytes();project=json.loads(blob)
    b=p.LoadBoard(str(board_path));fps={f.GetReference():f for f in b.GetFootprints()}
    pads={a.GetNumber():a for a in fps['U30'].Pads()}
    result=[];step=.05
    for pin in (args.pin or ['2','3','24','25','26']):
        pad=pads[pin];net=pad.GetNetname();code=pad.GetNetCode();at=s.XY(pad.GetPosition())
        ga=types.SimpleNamespace(width=.15,clearance=.15)
        g=s.Geometry(b,ga,project)
        domain=[max(100.,math.floor((at[0]-6)/step)*step),max(100.,math.floor((at[1]-6)/step)*step),
                min(160.,math.ceil((at[0]+6)/step)*step),min(160.,math.ceil((at[1]+6)/step)*step)]
        blocked,via=g.masks(domain,step,code,.15,.15);zi=g.layers.index(p.F_Cu);bi=g.layers.index(p.B_Cu)
        starts=s.adapters([(at,p.F_Cu)],(116.5,130),g,blocked,domain,step,code,.15,.15)
        dist={};parent={};queue=[]
        for (_,x,y),(cost,origin) in starts.items():
            dist[x,y]=cost;heapq.heappush(queue,(cost,x,y))
        end=None;count=0;ny,nx=blocked.shape[1:]
        while queue:
            cost,x,y=heapq.heappop(queue)
            if cost>dist[x,y]+1e-8:continue
            count+=1;pt=(round(domain[0]+x*step,7),round(domain[1]+y*step,7))
            if cost*step>6:continue
            goal_ok=args.via_box is None or (args.via_box[0]<=pt[0]<=args.via_box[2] and args.via_box[1]<=pt[1]<=args.via_box[3])
            if goal_ok and not via[y,x] and not blocked[bi,y,x] and g.via_ok(pt,code,.15):end=(x,y);break
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
                u,v=x+dx,y+dy
                if u<0 or v<0 or u>=nx or v>=ny or blocked[zi,v,u]:continue
                if dx and dy and (blocked[zi,y,u] or blocked[zi,v,x]):continue
                nc=cost+(math.sqrt(2) if dx and dy else 1)
                if nc<dist.get((u,v),float('inf')):
                    dist[u,v]=nc;parent[u,v]=(x,y);heapq.heappush(queue,(nc,u,v))
        if end is None:
            print('No local legal via escape:',pin,net,count,flush=True);result.append({'pin':pin,'net':net,'status':'blocked','expanded':count});continue
        states=[end]
        while states[-1] in parent:states.append(parent[states[-1]])
        states.reverse();pts=[at]+[(round(domain[0]+x*step,7),round(domain[1]+y*step,7)) for x,y in states]
        clean=[]
        for pt in pts:
            if clean and math.dist(clean[-1],pt)<1e-7:continue
            while len(clean)>1:
                a,z=clean[-2:]
                if abs((z[0]-a[0])*(pt[1]-z[1])-(z[1]-a[1])*(pt[0]-z[0]))>1e-7:break
                clean.pop()
            clean.append(pt)
        assert all(g.line_ok(a,z,p.F_Cu,code,.15,.15) for a,z in zip(clean,clean[1:])),net
        vx,vy=clean[-1]
        route={'net':net,'paths':[{'net':net,'layer':'F.Cu','width':.15,'points':clean}],
               'vias':[{'net':net,'x':vx,'y':vy,'diameter':.6,'drill':.3}]}
        s.add(b,route)
        result.append({'pin':pin,'net':net,'status':'escaped','path':clean,'via':[vx,vy],
                       'length_mm':sum(math.dist(a,z) for a,z in zip(clean,clean[1:])),'expanded':count})
        print('Escaped',pin,net,'via',vx,vy,'length',result[-1]['length_mm'],flush=True)
    p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(board_path),b);pro.write_bytes(blob)
    args.out.write_text(json.dumps({'fanouts':result,'native_unconnected':b.GetConnectivity().GetUnconnectedCount(False)},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
