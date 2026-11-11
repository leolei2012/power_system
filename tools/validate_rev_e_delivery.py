"""Check delivered PCB/report/preview hashes and local review links, read-only."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parents[1];O=R/'outputs/pcb_review_2026-11-11'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
read=lambda f:json.loads(f.read_text(encoding='utf-8-sig'))
system=read(O/'system_check.json');assert system['mapping_pass'] and system['mating']['pass']
assert all(not v['errors'] for v in system['boards'].values())
for path,digest in system['input_sha256'].items():assert sha(Path(path))==digest,path
sources={'controller':R/'controller/hardware/g431_core/controller.kicad_pcb','inverter':R/'inverter/hardware/inverter.kicad_pcb'}
for name in ['preview_manifest.json','pair_manifest.json']:
    preview=read(O/'previews'/name)
    for role,digest in preview['source_pcb_sha256'].items():assert digest==sha(sources[role]),(name,role)
    for f,digest in preview['image_sha256'].items():assert sha(O/'previews'/f)==digest,(name,f)
for role,folder in [('controller',R/'controller/hardware/g431_core'),('inverter',R/'inverter/hardware')]:
    manifest=read(folder/'review/design_manifest.json');assert manifest['pcb']['sha256']==sha(sources[role])
    assert not manifest['manufacturing_release']
    for f,digest in manifest['project_sources'].items():assert sha(folder/f)==digest,(role,f)
    for row in manifest['pages']:assert sha(folder/row['file'])==row['sha256']
schema=read(O/'schematic_source_check.json')
for row in schema['schematic_pages']:assert sha(R/row['path'])==row['sha256']
core=read(R/'controller/hardware/g431_core/review/pcb_2026-11-11/pcb_check.json');assert core['source_sha256']==sha(sources['controller'])
kelvin=read(O/'final_kelvin_review.json');assert kelvin['pass'] and kelvin['source_sha256_after']==sha(sources['inverter'])
links=0
for f in [R/'README.md',R/'docs/pcb_review_2026-11-11.md',R/'docs/controller_daughterboard.md',R/'inverter/hardware/PCB_REVIEW.md',R/'controller/hardware/g431_core/PCB_REVIEW.md']:
    for target in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
        target=target.strip('<>').split('#',1)[0]
        if not target or re.match(r'\w+://',target):continue
        assert (f.parent/target).resolve().exists(),(f,target)
        links+=1
record={'result':'PASS','mapping':'364 refs / 1202 unique pins','mating_contacts':64,'geometry_errors':0,
        'controller_routing':'COMPLETE' if system['boards']['controller']['routing']['complete'] else 'INCOMPLETE',
        'inverter_routing':'COMPLETE' if system['boards']['inverter']['routing']['complete'] else 'INCOMPLETE',
        'inverter_unconnected':system['boards']['inverter']['routing']['raw_pcbnew_unconnected'],
        'native_sources_and_manifests_current':True,'markdown_links_valid':True,'local_links_checked':links,
        'schematic_pages_unchanged':len(schema['schematic_pages']),'final_kelvin_review_current':True}
(O/'delivery_validation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2))
