"""Plot one recorded conversion without resampling or modifying its data."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('batch',type=Path);a=p.parse_args()
out=a.batch/'figures';out.mkdir(exist_ok=True)
for case in json.loads((a.batch/'summary.json').read_text())['cases']:
    if 'timing_trace' not in case:continue
    w=case['timing_trace'];t=[(v-w['time'][0])*1e9 for v in w['time']]
    fig,ax=plt.subplots(4,1,figsize=(10,8),sharex=True,layout='constrained')
    panels=[(('I_adc.Sample','Sample','#246c91'),('I_adc.ClkC','Comparator reset','#d78022')),
            (('I_adc.Valid','Valid','#268c5a'),('EOC','End of conversion','#b44251')),
            (('I_adc.Vp','Top plate P','#246c91'),('I_adc.Vn','Top plate N','#d78022')),
            (('D9','D9','#7659a2'),('D0','D0','#338c87'))]
    for axis,signals in zip(ax,panels):
        for name,label,color in signals:axis.plot(t,w[name],label=label,color=color,linewidth=1)
        axis.set_ylabel('Voltage (V)');axis.grid(alpha=.2);axis.legend(loc='upper right',ncol=2,fontsize=9)
        axis.set_ylim(-.15,2.05)
    ax[-1].set_xlabel('Time in representative cycle (ns)');ax[-1].set_xlim(0,t[-1])
    fig.suptitle(case['case']+' | observed conversion timing',fontsize=12)
    fig.savefig(out/(case['case']+'_timing.png'),dpi=160);plt.close(fig)
print(out)
