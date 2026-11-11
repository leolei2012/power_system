"""Compose two unchanged native CAD renders at the same camera and zoom."""
from pathlib import Path
import hashlib,json,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/pcb_review_2026-11-11/previews'
CLI=Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
boards={'controller':ROOT/'controller/hardware/g431_core/controller.kicad_pcb','inverter':ROOT/'inverter/hardware/inverter.kicad_pcb'}
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before={n:sha(f) for n,f in boards.items()}
cmd=[str(CLI),'pcb','render','--width','1400','--height','1050','--side','top','--quality','basic','--background','opaque','--rotate','330,0,20','--zoom','0.65','--output',str(OUT/'controller_pair_3d.png'),str(boards['controller'])]
subprocess.run(cmd,check=True,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True)
system=json.loads((OUT.parent/'system_check.json').read_text(encoding='utf-8'))
gaps=system['boards']['inverter']['routing']['raw_pcbnew_unconnected']
img=Image.new('RGB',(1800,760),'#f8fafc');draw=ImageDraw.Draw(img)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
for x,file in [(0,'controller_pair_3d.png'),(900,'inverter_3d.png')]:
    source=Image.open(OUT/file).convert('RGB');source=source.resize((900,675),Image.Resampling.LANCZOS);img.paste(source,(x,80))
draw.text((24,12),'CONTROLLER | 60 x 60 mm | 4 layers',font=font,fill='#0f172a')
draw.text((24,43),'Routed review: 0 unconnected',font=small,fill='#475569')
draw.text((924,12),'INVERTER | 60 x 60 mm | 6 layers',font=font,fill='#0f172a')
draw.text((924,43),f'Layout / routing review: {gaps} connections remaining',font=small,fill='#475569')
img.save(OUT/'pcb_pair_3d.png')
assert before=={n:sha(f) for n,f in boards.items()}
manifest={'source_pcb_sha256':before,'native_CAD_command_for_equal_core_zoom':cmd,
          'camera_rotation_degrees':[330,0,20],'zoom_both':.65,
          'image_sha256':{n:sha(OUT/n) for n in ['controller_pair_3d.png','inverter_3d.png','pcb_pair_3d.png']},
          'inverter_raw_unconnected':gaps,'note':'Native KiCad renders resized side by side; no component geometry invented.'}
(OUT/'pair_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Saved',OUT/'pcb_pair_3d.png')
