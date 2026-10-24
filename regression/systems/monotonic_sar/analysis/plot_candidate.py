"""Render observed spectra and export their unmodified sample sequences."""
import argparse,csv,json,math
from pathlib import Path
import matplotlib


def main():
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    p=argparse.ArgumentParser();p.add_argument('batch',type=Path);a=p.parse_args()
    summary=json.loads((a.batch/'summary.json').read_text());out=a.batch/'figures';out.mkdir(exist_ok=True)
    for case in summary['cases']:
        spectrum=case.get('spectrum')
        if spectrum is None:continue
        is_code='codes' in case
        if is_code:
            samples=case['codes'];times=[v['sample_time_s'] for v in case['conversions']];reference=512**2/2;ylabel='Output code'
        else:
            samples=case['held_diff_v'];times=case['sample_times_s'];reference=1.8**2/2;ylabel='Held differential voltage (V)'
        name=case['case']
        with (out/(name+'_samples.csv')).open('w',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['index','sample_time_s','code' if is_code else 'held_differential_v'])
            writer.writerows(zip(range(len(samples)),times,samples))
        fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained',gridspec_kw={'height_ratios':[1,2]})
        fig.suptitle(name+' | candidate simulation',fontsize=12)
        axes[0].plot(range(len(samples)),samples,linewidth=.85,color='#146c94');axes[0].set(xlabel='Consecutive sample index',ylabel=ylabel,xlim=(0,len(samples)-1));axes[0].grid(alpha=.18)
        x=[v/1e6 for v in spectrum['frequency_hz'][1:]]
        y=[10*math.log10(max(v,1e-30)/reference) for v in spectrum['power'][1:]]
        axes[1].vlines(x,-160,y,color='#167d8d',linewidth=.8);axes[1].plot(x,y,'.',color='#167d8d',markersize=2)
        axes[1].set(xlabel='Frequency (MHz)',ylabel='One-sided power (dBFS)',xlim=(0,spectrum['sample_rate_hz']/2e6),ylim=(-140,5));axes[1].grid(alpha=.18)
        sndr=f"{spectrum['sndr_db']:.3f} dB" if spectrum['sndr_db'] is not None else 'undefined (zero spectral power)'
        axes[1].text(.98,.96,f"SNDR {sndr}\nN={len(samples)}, rectangular window\nDC excluded from SNDR",transform=axes[1].transAxes,ha='right',va='top',fontsize=10)
        fig.savefig(out/(name+'_fft.png'),dpi=160);plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
