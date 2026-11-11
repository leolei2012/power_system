"""Refresh only compact embedded lib caches from the owning project library."""
from compact_revision import *

local=sx.load((B/'InverterLocal.kicad_sym').open(encoding='utf-8'))
lookup={x[1]:x for x in children(local,'symbol')}
updated=[]
for file in B.glob('*.kicad_sch'):
    data=sx.load(file.open(encoding='utf-8'));libs=child(data,'lib_symbols');dirty=False
    for index,entry in enumerate(libs):
        if tag(entry,'symbol') and entry[1] in ['InverterLocal:BSC110N15NS5','InverterLocal:MBRD20150CT_13']:
            replacement=copy.deepcopy(lookup[entry[1].split(':')[1]]);replacement[1]=entry[1]
            if replacement!=entry:libs[index]=replacement;dirty=True
    if dirty:dump(file,data);updated.append(file.name)
print('Synchronized project library caches:',updated)
