"""Run the pinned local six-layer router with an isolated data directory.

No design is uploaded. Input/output hashes, process options and result are
recorded next to the session. Native KiCad DRC governs acceptance of routing.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, subprocess, time

ROOT=Path(__file__).resolve().parents[3]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--dsn',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
ap.add_argument('--seconds',type=int,default=360);ap.add_argument('--passes',type=int,default=8)
ap.add_argument('--engine',choices=['2.5.0','2.1.0'],default='2.5.0')
ap.add_argument('--no-neckdown',action='store_true',help='Keep requested trace widths; do not automatically neck down at pins.')
ap.add_argument('--ignore-classes',default='',help='Comma-separated exact DSN class names already complete in native KiCad.')
args=ap.parse_args();args.dsn=args.dsn.resolve();args.out=args.out.resolve()
args.out.parent.mkdir(parents=True,exist_ok=True)
jar=ROOT/'.tools/freerouting-2.5.0/freerouting.jar'
if args.engine=='2.1.0':jar=ROOT/'.tools/freerouting-2.1.0-alternative/freerouting-2.1.0.jar'
java=ROOT/'.tools/freerouting-2.5.0/jdk-25.0.5+8-jre/bin/java.exe'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
data=ROOT/'.tools'/('compact_router_'+args.out.stem)
timeout=f'{args.seconds//3600:02d}:{args.seconds//60%60:02d}:{args.seconds%60:02d}'
cmd=[str(java),'-Xmx4g','-jar',str(jar),'-de',str(args.dsn),'-do',str(args.out),'-l','en','-da',
     '--user_data_path='+str(data),'--gui.enabled=false','--api_server.enabled=false',
     '--profile.allow_telemetry=false','--profile.allow_contact=false',
     '--usage_and_diagnostic_data.disable_analytics=true',
     '--router.fanout.enabled=false','--router.optimizer.enabled=false',
     '--router.job_timeout='+timeout,'--router.autorouter.max_passes='+str(args.passes),
     '--router.layers.routable=true,false,true,true,false,true']
if args.engine=='2.1.0':cmd+=['--router.max_passes='+str(args.passes)]
if args.no_neckdown:cmd+=['--router.automatic_neckdown=false']
if args.ignore_classes:cmd+=['--router.autorouter.ignore_net_classes='+args.ignore_classes]
manifest={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,
          'dsn_sha256':sha(args.dsn),'jar_sha256':sha(jar),'status':'running'}
report=args.out.with_suffix('.run.json');log=args.out.with_suffix('.log')
report.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Local route started:',args.out,'timeout',timeout,flush=True);start=time.monotonic()
try:
    with log.open('w',encoding='utf-8') as out:
        proc=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=args.seconds+60,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    manifest.update(status='completed' if proc.returncode==0 else 'failed',exit_code=proc.returncode)
except subprocess.TimeoutExpired:
    manifest.update(status='process_timeout')
manifest.update(elapsed_seconds=round(time.monotonic()-start,3),dsn_unchanged=sha(args.dsn)==manifest['dsn_sha256'])
if args.out.exists():manifest.update(session_sha256=sha(args.out),session_bytes=args.out.stat().st_size)
report.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k not in ['command']},indent=2),flush=True)
