"""Sync current XML component metadata into a placed/routed native board.

Does not change footprint identity, pads, nets, UUIDs, geometry or routing.
"""
from build_pcb import *
import argparse

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--board',type=Path,default=BOARD_PATH)
args=ap.parse_args();target=args.board.resolve();project=target.with_suffix('.kicad_pro');saved=project.read_bytes()
board=p.LoadBoard(str(target));fps={f.GetReference():f for f in board.GetFootprints()}
for c in ET.parse(REVIEW/'inverter.net.xml').getroot().findall('./components/comp'):
    f=fps[c.attrib['ref']];assert f.GetFPIDAsString()==c.findtext('footprint')
    f.SetValue(c.findtext('value'));f.SetDNP(any(x.attrib['name']=='dnp' for x in c.findall('property')))
    for field in c.findall('./fields/field'):
        if field.attrib['name'] not in ['Reference','Value','Footprint','ki_fp_filters']:f.SetField(field.attrib['name'],field.text or '')
    for prop in c.findall('property'):
        if prop.attrib['name'] not in ['Sheetname','Sheetfile','dnp','ki_fp_filters']:f.SetField(prop.attrib['name'],prop.attrib.get('value',''))
    for field in f.GetFields():
        if field.GetName() not in ['Reference','Value']:field.SetVisible(False)
p.SaveBoard(str(target),board);project.write_bytes(saved)
print('Synchronized placed-board component metadata')
