"""Clamp router neck-downs to the owning board's 0.15 mm trace minimum.

Run actual DRC after this operation; widening is never assumed clearance-safe.
Fixed main-power/Kelvin copper is not changed.
"""
from build_pcb import *
import argparse

ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--board',type=Path,default=BOARD_PATH)
ap.add_argument('--report',type=Path,default=REVIEW/'compact_neckdowns.json');args=ap.parse_args()
board=p.LoadBoard(str(args.board));project=args.board.with_suffix('.kicad_pro');saved=project.read_bytes();changed=[]
for t in board.GetTracks():
    if isinstance(t,p.PCB_VIA):
        t.SetFrontTentingMode(p.TENTING_MODE_TENTED);t.SetBackTentingMode(p.TENTING_MODE_TENTED)
    elif not t.IsLocked() and t.GetWidth()<MM(.15):
        changed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'from_mm':p.ToMM(t.GetWidth()),'to_mm':.15})
        t.SetWidth(MM(.15))
p.SaveBoard(str(args.board),board);project.write_bytes(saved)
args.report.write_text(json.dumps({'changed':changed,'note':'Re-run native filled-zone DRC; no design rules lowered.'},indent=2)+'\n',encoding='utf-8')
print('Widened router neck-downs:',len(changed))
