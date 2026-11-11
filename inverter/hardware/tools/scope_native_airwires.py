"""Split complete nets into explicitly ignored DSN classes, using native DRC."""
from pathlib import Path
import argparse,json,re,sexpdata as sx,hashlib
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--dsn',required=True,type=Path);ap.add_argument('--drc',required=True,type=Path)
ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
source=a.dsn.read_text(encoding='utf-8');drc=json.loads(a.drc.read_text(encoding='utf-8'))
norm=lambda s:str(s).replace('{slash}','/')
pending=set()
for gap in drc['unconnected_items']:
    for item in gap['items']:pending.update(norm(n) for n in re.findall(r'\[([^]]+)\]',item['description']))
def end_scope(start):
    depth=0;quoted=False;escape=False
    for pos in range(start,len(source)):
        c=source[pos]
        if quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:return pos+1
    raise ValueError('Unclosed class')
changes=[];ignored=[];active=[]
for m in re.finditer(r'\(class\s',source):
    end=end_scope(m.start());data=sx.loads(source[m.start():end])
    split=next((i for i in range(2,len(data)) if isinstance(data[i],list)),len(data))
    members=data[2:split];tail=data[split:];scopes=[]
    todo=[x for x in members if norm(x) in pending];done=[x for x in members if norm(x) not in pending]
    if todo:scopes.append(sx.dumps(data[:2]+todo+tail));active.extend(norm(x) for x in todo)
    if done:
        name='Done_'+str(data[1]);ignored.append(name)
        scopes.append(sx.dumps([data[0],name]+done+tail))
    changes.append((m.start(),end,'\n    '.join(scopes)))
assert changes and set(active)==pending,('Native pending net absent from DSN',pending-set(active))
for start,end,repl in reversed(changes):source=source[:start]+repl+source[end:]
a.out.write_text(source,encoding='utf-8')
report={'dsn':str(a.dsn),'dsn_sha256':hashlib.sha256(a.dsn.read_bytes()).hexdigest(),
        'native_drc':str(a.drc),'native_drc_sha256':hashlib.sha256(a.drc.read_bytes()).hexdigest(),
        'active_nets':sorted(pending),'ignored_classes':ignored,'no_circuit_nets_removed':True}
a.out.with_suffix('.scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Active nets:',len(pending),'--ignore-classes',','.join(ignored))
