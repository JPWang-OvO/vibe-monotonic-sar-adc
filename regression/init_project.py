"""Initialize this ADC's configuration while retaining template examples."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def save(name, data):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')

save('project.json', dict(schema_version=1, project_id='MONOTONIC_SAR',
    design_library='MONOTONIC_SAR', process='config/processes/tsmc18.json', flows=[]))
save('config/run_budget.json', dict(start_utc='2026-10-23T06:40:35Z',
    deadline_utc='2026-10-23T18:40:35Z', max_workers=14, threads_per_worker=8,
    collect_reserve_seconds=900))
save('config/environments/tsmc18.local.json', dict(profile='<bridge-profile>',
    remote_runs='<remote-runs>',
    server_python='<server-python>', spectre='<spectre-executable>',
    cadence_setup=None,
    model_files={'tsmc18':'<model-file>'},
    oa_library_path='<oa-library-path>'))
save('config/architecture.json', dict(bits=10, fs_hz=50e6, clock_hz=250e6,
    vdd=1.8, vrefp=1.8, vrefn=0.0, vcm=0.9, amplitude_dbfs=-1,
    fft_n=256, fft_bins=[3,51], sndr_threshold_db=[57,56.5],
    weights=[256,128,64,32,16,8,4,2,1], dummy_weight=1, unit_cap_f=20e-15,
    equal_decision=1, code_format='offset_binary', bit_order='MSB_first',
    sampling_window_s=4e-9, conversion_window_s=16e-9))
