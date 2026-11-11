"""Local four-layer GPIO routing interchange for the current Rev E core.

No schematic generation or placement. Preserve every locked native seed item.
The pinned local router runs offline with analytics/contact disabled.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
import pcbnew as p

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
BOARD=BASE/'controller.kicad_pcb'
OUT=BASE/'review/pcb_2026-11-11/routing'
DSN=OUT/'controller.dsn'
SES=OUT/'controller.ses'
STATE=OUT/'source.json'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def fixed(board):
    out={}
    for t in board.GetTracks():
        if not t.IsLocked():continue
        if isinstance(t,p.PCB_VIA):
            a=t.GetPosition();record=['via',t.GetNetname(),a.x,a.y,t.GetWidth(p.F_Cu),t.GetDrillValue(),t.TopLayer(),t.BottomLayer()]
        else:
            a,z=t.GetStart(),t.GetEnd();record=['track',t.GetNetname(),t.GetLayer(),a.x,a.y,z.x,z.y,t.GetWidth()]
        out[t.m_Uuid.AsString()]=record
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=['export','route','import'])
    ap.add_argument('--seconds',type=int,default=120)
    ap.add_argument('--passes',type=int,default=8)
    args=ap.parse_args();OUT.mkdir(exist_ok=True,parents=True)
    if args.stage=='export':
        b=p.LoadBoard(str(BOARD));assert b.GetCopperLayerCount()==4
        before=fixed(b);b.BuildConnectivity();assert before==fixed(b)
        assert p.ExportSpecctraDSN(b,str(DSN))
        state={'source_sha256':sha(BOARD),'project_sha256':sha(BOARD.with_suffix('.kicad_pro')),
               'dsn_sha256':sha(DSN),'fixed_items':before,'source_unconnected':b.GetConnectivity().GetUnconnectedCount(False)}
        STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
        print('Exported current four-layer board:',state['source_unconnected'],'raw gaps;',len(before),'fixed items.')
    elif args.stage=='route':
        state=json.loads(STATE.read_text(encoding='utf-8'));assert sha(DSN)==state['dsn_sha256']
        java=ROOT/'.tools/freerouting-2.5.0/jdk-25.0.5+8-jre/bin/java.exe'
        jar=ROOT/'.tools/freerouting-2.5.0/freerouting.jar'
        timeout=f'{args.seconds//3600:02d}:{args.seconds//60%60:02d}:{args.seconds%60:02d}'
        cmd=[str(java),'-Xmx2g','-jar',str(jar),'-de',str(DSN),'-do',str(SES),'-l','en','-da',
             '--user_data_path='+str(OUT/'router_data'),'--gui.enabled=false','--api_server.enabled=false',
             '--profile.allow_telemetry=false','--profile.allow_contact=false',
             '--usage_and_diagnostic_data.disable_analytics=true',
             '--router.fanout.enabled=false','--router.optimizer.enabled=false',
             '--router.job_timeout='+timeout,'--router.autorouter.max_passes='+str(args.passes),
             '--router.layers.routable=true,false,true,true']
        info={'command':cmd,'jar_sha256':sha(jar),'source_sha256':state['source_sha256'],'status':'running'}
        report=OUT/'router_run.json';report.write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
        start=time.monotonic();print('Local core GPIO routing started.',flush=True)
        try:
            with (OUT/'router.log').open('w',encoding='utf-8') as log:
                done=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=args.seconds+30,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            info.update(status='complete' if done.returncode==0 else 'failed',exit_code=done.returncode)
        except subprocess.TimeoutExpired:info['status']='timeout'
        info.update(seconds=round(time.monotonic()-start,3),dsn_unchanged=sha(DSN)==state['dsn_sha256'])
        if SES.exists():info.update(session_sha256=sha(SES),session_bytes=SES.stat().st_size)
        report.write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in info.items() if k!='command'},indent=2),flush=True)
    else:
        state=json.loads(STATE.read_text(encoding='utf-8'))
        assert sha(BOARD)==state['source_sha256'],'Source changed while router was running.'
        pro=BOARD.with_suffix('.kicad_pro');pro_bytes=pro.read_bytes()
        b=p.LoadBoard(str(BOARD));assert fixed(b)==state['fixed_items']
        assert p.ImportSpecctraSES(b,str(SES))
        assert fixed(b)==state['fixed_items'],'Router changed locked local copper.'
        assert all(t.GetNetname()=='GND' for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetLayer()==p.In1_Cu),'Ordinary signal entered continuous GND reference layer.'
        p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
        assert fixed(b)==state['fixed_items']
        assert p.SaveBoard(str(BOARD),b);pro.write_bytes(pro_bytes)
        report={'status':'SESSION IMPORTED; native DRC required','source_sha256':state['source_sha256'],
                'board_sha256':sha(BOARD),'fixed_items_preserved':len(state['fixed_items']),
                'native_unconnected':b.GetConnectivity().GetUnconnectedCount(False),
                'tracks':sum(not isinstance(t,p.PCB_VIA) for t in b.GetTracks()),
                'vias':sum(isinstance(t,p.PCB_VIA) for t in b.GetTracks())}
        (OUT/'import.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2))


if __name__=='__main__':main()
