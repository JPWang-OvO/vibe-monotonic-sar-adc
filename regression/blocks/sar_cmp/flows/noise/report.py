"""Render collected standalone noise probabilities and fitted sigma."""
import argparse
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('batch',type=Path);a=p.parse_args()
    batch=json.loads((a.batch/'batch.json').read_text())
    cases={c['id']:c for c in batch['cases']}
    results=json.loads((a.batch/'summary.json').read_text())['cases']
    folder=a.batch/'figures';folder.mkdir(exist_ok=True)
    fig,axes=plt.subplots(len(results),3,figsize=(12,2.5*len(results)),squeeze=False)
    lines=['# Standalone comparator transient noise','',
           '| Case | CM V | Sigma mV | Offset mV | Sigma SE mV | Unresolved | Valid late | Reset errors | Max Valid delay ns |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for i,result in enumerate(results):
        assert result['execution_pass'] and result['measurement_pass'] and result['log_audit']['pass']
        name=result['case'];m=result['metrics']
        for j,curve in enumerate(result['curves']):
            ax=axes[i,j];fit=curve['fit'];rows=curve['points'];cm=curve['common_mode_v']
            x=[r['differential_v']*1e3 for r in rows];n=[r['resolved'] for r in rows]
            probability=[r['ones']/r['resolved'] if r['resolved'] else float('nan') for r in rows]
            ax.plot(x,probability,'o',label='128 trials/level',ms=4)
            if fit['identifiable']:
                xx=[-3+6*k/200 for k in range(201)]
                yy=[.5*math.erfc(-(v*1e-3-fit['offset_v'])/fit['sigma_v']/math.sqrt(2)) for v in xx]
                ax.plot(xx,yy,label=f'sigma={fit["sigma_v"]*1e3:.3f} mV')
                values=[f'{fit[k]*1e3:.4f}' for k in ('sigma_v','offset_v','sigma_standard_error_v')]
            else:values=['unidentified']*3
            ax.set(title=f'{cases[name]["condition"]["id"]}, CM={cm:g} V',xlabel='Differential input (mV)',ylabel='P(Outp=1)',ylim=(-.03,1.03))
            ax.grid(alpha=.2);ax.legend(fontsize=8)
            lines.append(f'| {cases[name]["condition"]["id"]} | {cm:g} | '+' | '.join(values)+
                         f' | {sum(r["unresolved"] for r in rows)} | {sum(r["valid_late"] for r in rows)} | {m["reset_errors"]} | {m["delay_max_s"]*1e9:.3f} |')
    fig.tight_layout();fig.savefig(folder/'probability.png',dpi=140);fig.savefig(folder/'probability.svg');plt.close(fig)
    corners=list(dict.fromkeys((cases[r['case']]['condition']['corner'],cases[r['case']]['condition']['tokens']['TEMP']) for r in results))
    fig,grid=plt.subplots(1,len(corners),figsize=(4.5*len(corners),4.2),sharey=True,squeeze=False);axes=grid[0]
    for ax,(corner,temperature) in zip(axes,corners):
        for result in results:
            condition=cases[result['case']]['condition']
            if (condition['corner'],condition['tokens']['TEMP'])!=(corner,temperature):continue
            curves=result['curves'];width=condition['id'].split('_')[0][2:]
            ax.errorbar([c['common_mode_v'] for c in curves],[c['fit']['sigma_v']*1e3 for c in curves],
                        yerr=[c['fit']['sigma_standard_error_v']*1e3 for c in curves],marker='o',capsize=3,label=width+' um input pair')
        ax.set(xscale='log',xlabel='Input common mode (V)',title=corner.upper()+' / '+str(temperature)+' C')
        ax.invert_xaxis();ax.set_xticks([.9,.1125,.0017578125],['0.9','0.1125','0.001758']);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Input-referred noise sigma (mV RMS)')
    fig.text(.5,.015,'128 trials/level; decisions at 1.8 ns.\nError bars: binomial fit SE.\nTemporal correlation excluded.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.12,1,1));fig.savefig(folder/'sigma.png',dpi=160);fig.savefig(folder/'sigma.svg');plt.close(fig)
    lines+=['','Noise includes comparator and actual bias circuit. Ideal clock/inputs; Outp/Outn 20 fF each, Valid 50 fF.',
            'Decision deadline 1.8 ns; period 4 ns. Fits with unresolved or reset errors require waveform review.',
            'SE assumes independent binomial trials; temporal correlation and mismatch are excluded.','']
    (a.batch/'noise-report.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print('\n'.join(lines))


if __name__=='__main__':main()
