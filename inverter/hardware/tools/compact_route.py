"""Local Specctra interchange for the six-layer compact revision.

Never generate placement here. Native fixed power/Kelvin copper remains the
owner; only the intermediate DSN changes reference-layer type for the router.
"""
from build_pcb import *
import argparse

def fixed_geometry(board):
    result={}
    for t in board.GetTracks():
        if not t.IsLocked():continue
        if isinstance(t,p.PCB_VIA):
            value=('via',t.GetNetname(),t.GetPosition().x,t.GetPosition().y,
                   t.GetWidth(p.F_Cu),t.GetDrillValue(),t.TopLayer(),t.BottomLayer())
        else:
            value=('track',t.GetNetname(),t.GetLayer(),t.GetStart().x,t.GetStart().y,
                   t.GetEnd().x,t.GetEnd().y,t.GetWidth())
        result[t.m_Uuid.AsString()]=value
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board',type=Path,default=BOARD_PATH)
    ap.add_argument('--export-dsn',type=Path)
    ap.add_argument('--import-session',type=Path)
    args=ap.parse_args()
    assert bool(args.export_dsn)!=bool(args.import_session)
    board=p.LoadBoard(str(args.board));assert board.GetCopperLayerCount()==6
    if args.export_dsn:
        locked=fixed_geometry(board);board.BuildConnectivity()
        assert locked==fixed_geometry(board),'Connectivity changed fixed copper nets or geometry'
        assert p.ExportSpecctraDSN(board,str(args.export_dsn))
        source=args.export_dsn.read_text(encoding='utf-8')
        for layer in ['In1.Cu','In4.Cu']:
            source,n=re.subn(r'(\(layer '+re.escape(layer)+r'\s+\(type )power(\))',r'\1signal\2',source,count=1)
            assert n==1,('missing native ground reference',layer)
        args.export_dsn.write_text(source,encoding='utf-8')
        print('Exported',args.export_dsn)
    else:
        pro=args.board.with_suffix('.kicad_pro');contents=pro.read_bytes()
        locked=fixed_geometry(board)
        assert p.ImportSpecctraSES(board,str(args.import_session))
        after=fixed_geometry(board)
        assert locked==after,('session modified locked copper',len(locked),len(after))
        assert all(t.GetNetname()=='GND' for t in board.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetLayer() in [p.In1_Cu,p.In4_Cu])
        board.BuildConnectivity()
        assert locked==fixed_geometry(board),'Connectivity changed fixed copper after session import'
        p.SaveBoard(str(args.board),board);pro.write_bytes(contents)
        print('Imported session; native raw gaps',board.GetConnectivity().GetUnconnectedCount(False))

if __name__=='__main__':main()
