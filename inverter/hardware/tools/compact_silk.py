"""Add readable power-port names on the compact owning PCB; DRC afterwards."""
from build_pcb import *

board=p.LoadBoard(str(BOARD_PATH));pro=B/'inverter.kicad_pro';saved=pro.read_bytes()
labels=[('DC+',1.45,8.5,90),('DC-',1.45,14.5,90),('U',59.1,12.7,0),('V',59.1,27.7,0),
        ('W',59.1,42.7,0),('BR+',38,54.0,0),('BR_SW',44,53.2,0)]
for value,x,y,rotation in labels:
    existing=[old for old in board.GetDrawings() if isinstance(old,p.PCB_TEXT) and old.GetText()==value and old.GetLayer()==p.F_SilkS]
    assert len(existing)<=1,('duplicate terminal name',value)
    item=existing[0] if existing else text(board,value,x,y,p.F_SilkS,.8)
    item.SetPosition(V(x,y));item.SetTextAngle(p.EDA_ANGLE(rotation,p.DEGREES_T))
p.SaveBoard(str(BOARD_PATH),board);pro.write_bytes(saved)
print('Power terminal silkscreen names added; run current DRC')
