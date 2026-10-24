"""Report the original 20 conditions for the selected low-power DUT."""
import argparse
import json
import re
from pathlib import Path
from regression.common.project import ROOT,read_json,write_json
from regression.common.measure import criterion


def main():
    parser=argparse.ArgumentParser();parser.add_argument('batches',nargs='*',type=Path)
    parser.add_argument('--case',nargs=2,action='append',default=[],metavar=('BATCH','CASE'));args=parser.parse_args()
    if not args.batches and not args.case:parser.error('Supply batches or explicit --case selections')
    fixed=read_json(ROOT/'config/acceptance_lowpower.json');design=read_json(ROOT/'config/lowpower_design.json')
    baseline=read_json(ROOT/'config/acceptance_results.json')
    previous={(r['corner'],r['temp_c'],r['noise'],r['k']):r for r in baseline['cases']}
    expected={(c,t,n,k) for c,t in [('tt',25),('ss',-40),('ss',125),('ff',-40),('ff',125)]
              for n in (False,True) for k in (3,51)}
    seen=set();rows=[];reference=None;source_equal=True
    noise_spec=f'noisefmin={fixed["noise"]["noisefmin_hz"]:.12g} noisefmax={fixed["noise"]["noisefmax_hz"]:.12g} noiseseed={fixed["noise"]["seed"]}'
    groups=[(folder,None) for folder in args.batches]+[(Path(folder),{case}) for folder,case in args.case]
    for folder,selected_cases in groups:
        batch=read_json(folder/'batch.json');settings={c['id']:c for c in batch['cases']}
        results=read_json(folder/'summary.json')['cases']
        if selected_cases is not None:assert selected_cases<={r['case'] for r in results}
        for result in results:
            if selected_cases is not None and result['case'] not in selected_cases:continue
            case=settings[result['case']];condition=case['condition'];cfg=case['measurement']
            assert case['sources']['cell_views']==design['cell_views']
            assert cfg['n']==256 and cfg['fft'] and cfg['physical_frontend']
            for key in ('discard_cycles','read_offset_s','logic_low_v','logic_high_v'):assert cfg[key]==fixed[key],key
            noise=bool(condition['tokens']['NOISE']);assert condition['tokens']['NOISE']==(noise_spec if noise else '')
            k=round(float(condition['tokens']['FIN'])*256/50e6)
            key=(condition['corner'],condition['tokens']['TEMP'],noise,k)
            assert key in expected and key not in seen,('Unexpected or duplicate condition',key);seen.add(key)
            assert case['criteria']['sndr_db']['min']==fixed['sndr_min_db']['k'+str(k)]
            criteria=set(fixed['functional_criteria'])|{'sndr_db'}
            if key[0]=='tt':
                criteria.add('core_power_w');assert case['criteria']['core_power_w']['max']<=fixed['tt_core_power_max_w']
            assert set(case['criteria'])==criteria,case['criteria']
            inputs=folder/'cases'/case['id']/'inputs'
            sources={n:(inputs/n).read_text() for n in case['sources']['sources'] if n!=case['sources']['entry']}
            if reference is None:reference=sources
            else:source_equal=source_equal and sources==reference
            actual_noise={}
            if noise:
                assert noise_spec in (inputs/case['sources']['entry']).read_text()
                log=(folder/'cases'/case['id']/'logs/spectre.log').read_text(errors='replace')
                for parameter in ('noisefmin','noisefmax'):
                    match=re.search(r'^\s*'+parameter+r'\s*=\s*([\d.eE+-]+)\s+(Hz|kHz|MHz|GHz)\s*$',log,re.M)
                    assert match,(parameter,case['id'])
                    actual_noise[parameter+'_hz']=float(match[1])*{'Hz':1,'kHz':1e3,'MHz':1e6,'GHz':1e9}[match[2]]
            assert result['execution_pass'] and result['measurement_pass'],('Incomplete measurement',case['id'])
            metrics=result['metrics'];power=result['power']
            checks=dict(result['checks'])
            if key[0]=='tt':checks['core_power_w']=criterion(metrics['core_power_w'],{'max':fixed['tt_core_power_max_w']})
            rows.append(dict(batch=folder.name,case=case['id'],corner=key[0],temp_c=key[1],noise=noise,k=k,
                passed=all(checks.values()),original_batch_pass=bool(result.get('pass')),execution_pass=result.get('execution_pass'),measurement_pass=result.get('measurement_pass'),
                metrics=metrics,power=power,noise_actual=actual_noise,
                sndr_delta_from_checkpoint_db=metrics['sndr_db']-previous[key]['metrics']['sndr_db'],
                core_power_vs_paper=power['total_without_output_buffers_w']/.000826,
                failed_checks=[n for n,v in checks.items() if not v]))
    rows.sort(key=lambda r:(r['corner'],r['temp_c'],r['noise'],r['k']))
    complete=seen==expected and source_equal and all(r['passed'] for r in rows)
    report=dict(all_electrical_pass=complete,dut_sources_equal=source_equal,cell_views=design['cell_views'],required_cases=20,
                completed_cases=len(rows),passed_cases=sum(r['passed'] for r in rows),cases=rows,
                batches=list(dict.fromkeys(str(p.resolve()) for p,_ in groups)),explicit_case_selections=args.case,
                missing_cases=[list(k) for k in sorted(expected-seen)])
    report['optimization_sndr_target_range_db']=fixed['optimization_sndr_target_range_db']
    report['below_optimization_target']=[r['case'] for r in rows if r['metrics']['sndr_db']<fixed['optimization_sndr_target_range_db'][0]]
    write_json(ROOT/'config/acceptance_lowpower_results.json',report)
    design['status']='electrical_pass_oa_pending' if complete else 'electrical_acceptance_incomplete'
    write_json(ROOT/'config/lowpower_design.json',design)
    lines=['---','title: 低功耗候选电气验收','type: verification-method','status: active','last_reviewed: 2026-10-25',
           'authoritative_sources:','  - ../../config/acceptance_lowpower_results.json','  - ../../config/lowpower_design.json',
           '  - ../../config/acceptance_lowpower.json','---','','# 验收结果','',
           f'同一 DUT 完成 {len(rows)}/20 项，{report["passed_cases"]} 项通过。',
           '全部电气验收通过。原生网表及图面核对见 [低功耗 OA 交付](lowpower-oa-delivery.md)。' if complete else '尚未满足全部电气验收。','',
           '每项采用丢弃 16 周期后的连续 256 个原始输出码，统一在 Sample 下降后 18 ns 读码。',
           '十次比较和唯一 EOC 必须在下一 Sample 上升沿前完成；输出寄存器保持结果直到下一 EOC。',
           '噪声设置为 1 Hz–50 GHz、seed=1；Spectre 19.1 按 5.8 µs 时长将实际下限设为约 172.414 kHz。',
           '核心功耗包含参考供电并扣除输出缓冲；论文比较值为 0.826 mW。','',
           f'TT 核心功耗门槛为 {fixed["tt_core_power_max_w"]*1e3:g} mW；旧批次保留原判据，本表以当前门槛复核已测功耗。','',
           f'SNDR 优化目标为 59–60 dB；实测 {len(report["below_optimization_target"])} 项低于 59 dB。低频/中频验收下限为 57/56.5 dB。','',
           '| 工艺/温度 | 噪声 | k | SNDR dB | 相对 checkpoint dB | 核心 mW | /论文 | EOC 至下次采样 ns | 结果 |',
           '|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in rows:
        m=r['metrics'];power=r['power']
        lines.append(f'| {r["corner"].upper()}/{r["temp_c"]} | {"开" if r["noise"] else "关"} | {r["k"]} | '
                     f'{m["sndr_db"]:.3f} | {r["sndr_delta_from_checkpoint_db"]:+.3f} | '
                     f'{power["total_without_output_buffers_w"]*1e3:.4f} | {r["core_power_vs_paper"]:.3f} | '
                     f'{m["timing_margin_min_s"]*1e9:.3f} | {"通过" if r["passed"] else ", ".join(r["failed_checks"])} |')
    lines+=['','# 供电功耗分项','',
            '| 工艺/温度 | 噪声 | k | VDD mW | VREFP mW | 含输出缓冲 mW | 输出缓冲 mW | 时钟输入 mW |',
            '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        p=r['power'];values=[f'{p[n]*1e3:.4f}' for n in ('VDD_w','VREFP_w','total_with_buffers_w','output_buffers_w','clock_input_w')]
        lines.append(f'| {r["corner"].upper()}/{r["temp_c"]} | {"开" if r["noise"] else "关"} | {r["k"]} | '+' | '.join(values)+' |')
    lines+=['','批次保存实际码、频谱、逐位轨迹、模块功耗和完整日志；SOA 警告保留在结果中。',
            '验证覆盖固定 256 点、单种子及规定的 PVT 矩阵；失配 Monte Carlo、DNL/INL 和全频段扫描尚未验证。','']
    (ROOT/'docs/verification/lowpower-acceptance.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ('all_electrical_pass','dut_sources_equal','completed_cases','passed_cases')}))


if __name__=='__main__':main()
