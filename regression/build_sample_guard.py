"""Hold comparator reset through the measured 0.50 ns bootstrap turn-off."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body=''
for i in range(8):
    body+=f'I_d{i} ({"A" if i==0 else "N"+str(i-1)} {"Delayed" if i==7 else "N"+str(i)} VDD VSS) INVD1BWP7T\n'
body+=mos('Mn0','HoldN A VSS VSS','nch',2)+mos('Mn1','HoldN Delayed VSS VSS','nch',2)
body+=mos('Mp0','P0 A VDD VDD','pch',4)+mos('Mp1','HoldN Delayed P0 VDD','pch',4)
body+='I_drive (HoldN Z VDD VSS) SAR_DRIVE scale=1\n'
save('logic','SAR_SAMPLE_GUARD',['A','Z','VDD','VSS'],body,
    'include "../../../../support/standard_cells/INVD1BWP7T/spectre/netlist.scs"\ninclude "../../../logic/SAR_DRIVE/transistor/netlist.scs"\n')
base='library/blocks/control/SAR_ASYNC'
s=(ROOT/(base+'/fast5/netlist.scs')).read_text().replace('SAR_DELAY4','SAR_SAMPLE_GUARD')
write(base+'/physical/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['physical']={'netlist':'physical/netlist.scs'};js(base+'/cell.json',m)
