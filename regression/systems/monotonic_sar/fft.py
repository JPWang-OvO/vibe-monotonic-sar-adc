"""Coherent rectangular-window SNDR; DC excluded, all other bins retained."""
import numpy as np

def spectrum(samples, fs, fundamental_bin):
    x=np.asarray(samples,dtype=float)
    if x.ndim!=1 or len(x)<4 or not np.all(np.isfinite(x)):
        raise ValueError('Expected a finite one-dimensional sample record')
    n=len(x)
    if not 0<fundamental_bin<n/2:
        raise ValueError('Fundamental must lie strictly between DC and Nyquist')
    power=np.abs(np.fft.rfft(x)/n)**2
    power[1:-1 if n%2==0 else None]*=2
    signal=power[fundamental_bin]
    mask=np.ones(len(power),dtype=bool)
    mask[[0,fundamental_bin]]=False
    residual=float(power[mask].sum())
    return dict(sndr_db=float(10*np.log10(signal/residual)),
        signal_power=float(signal),noise_distortion_power=residual,
        dc_power=float(power[0]),frequency_hz=(np.arange(len(power))*fs/n).tolist(),
        power=power.tolist(),sample_rate_hz=float(fs),samples=n)

def validate_known_signals():
    n=256
    phase=2*np.pi*np.arange(n)/n
    # A 0.01-amplitude second harmonic must produce precisely 40 dB SNDR.
    result=spectrum(7+np.sin(3*phase)+0.01*np.cos(6*phase),50e6,3)
    assert abs(result['sndr_db']-40)<1e-9
    assert abs(result['signal_power']-.5)<1e-12
    assert abs(result['dc_power']-49)<1e-12
    # Nyquist has one side only: variance of 0.01*(-1)^n is 0.0001.
    result2=spectrum(np.sin(3*phase)+.01*(-1.)**np.arange(n),50e6,3)
    assert abs(result2['noise_distortion_power']-.0001)<1e-12
    assert abs(sum(result2['power'])-.5001)<1e-12
    return dict(harmonic_sndr_db=result['sndr_db'],nyquist_power=result2['noise_distortion_power'],pass_all=True)
