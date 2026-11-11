"""Route actual KiCad airwire nets only; leave already connected nets alone.

Run with regular Python + sexpdata after exporting the continuation DSN.
Router graph approximations can see false gaps at filled pours and old stubs;
the owning native KiCad DRC determines which nets still require work.
"""
from pathlib import Path
import json
import re
import sexpdata as sx

B=Path(__file__).resolve().parents[1]
source=(B/'review/inverter_route_resume.dsn').read_text(encoding='utf-8')
drc=json.loads((B/'review/pcb_drc.json').read_text(encoding='utf-8'))
pending=set()
for missing in drc['unconnected_items']:
    for item in missing['items']:pending.update(re.findall(r'\[([^]]+)\]',item['description']))

def end_scope(text,start):
    depth=0;quoted=False;escape=False
    for pos in range(start,len(text)):
        c=text[pos]
        if quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:return pos+1
    raise ValueError('Unclosed class scope')

replacements=[];ignored=[];active=[]
for match in re.finditer(r'\(class\s',source):
    end=end_scope(source,match.start());data=sx.loads(source[match.start():end])
    split=next((i for i in range(2,len(data)) if isinstance(data[i],list)),len(data))
    members=data[2:split];tail=data[split:]
    todo=[x for x in members if str(x) in pending];done=[x for x in members if str(x) not in pending]
    scopes=[]
    if todo:
        scopes.append(sx.dumps(data[:2]+todo+tail));active.extend(map(str,todo))
    if done:
        name='Done_'+str(data[1]);ignored.append(name)
        scopes.append(sx.dumps([data[0],sx.Symbol(name)]+done+tail))
    replacements.append((match.start(),end,'\n    '.join(scopes)))
assert replacements and set(active)==pending,('Pending net absent from DSN',pending-set(active))
for start,end,replacement in reversed(replacements):source=source[:start]+replacement+source[end:]
target=B/'review/inverter_route_scoped.dsn';target.write_text(source,encoding='utf-8')
(B/'review/pcb_route_scope.json').write_text(json.dumps({'pending_nets':sorted(pending),'ignored_classes':ignored,'source':'Actual native KiCad DRC; no circuit nets removed from the board or DSN.'},indent=2)+'\n',encoding='utf-8')
print('Active nets:',len(pending),'Ignore:',','.join(ignored))
