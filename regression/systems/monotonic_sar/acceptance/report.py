"""Collect the fixed electrical matrix and power results for one delivered DUT."""
import argparse,json,re
from pathlib import Path
from regression.common.project import ROOT,read_json,write_json


def main():

    p=argparse.ArgumentParser();p.add_argument('batches',nargs='+',type=Path);a=p.parse_args()
    final=read_json(ROOT/'config/final_design.json');fixed=read_json(ROOT/'config/acceptance.json')
    rows=[];seen=set();reference_sources=None;source_equal=True
    for folder in a.batches:
        batch=read_json(folder/'batch.json');summary=read_json(folder/'summary.json')
        settings={c['id']:c for c in batch['cases']}
        for result in summary['cases']:
            c=settings[result['case']];condition=c['condition'];cfg=c['measurement']
            assert c['sources']['cell_views']==final['cell_views']
            assert cfg['n']==256 and cfg['fft'] and cfg['discard_cycles']==fixed['discard_cycles']
            noise=bool(condition['tokens']['NOISE'])
            noise_spec=f'noisefmin={fixed["noise"]["noisefmin_hz"]:.12g} noisefmax={fixed["noise"]["noisefmax_hz"]:.12g} noiseseed={fixed["noise"]["seed"]}'
            assert condition['tokens']['NOISE']==(noise_spec if noise else '')
            k=round(float(condition['tokens']['FIN'])*256/50e6)
            key=(condition['corner'],condition['tokens']['TEMP'],noise,k)
            assert key not in seen,('Duplicate formal case',key);seen.add(key)
            assert k in (3,51) and c['criteria']['sndr_db']['min']==(57.0 if k==3 else 56.5)
            inputs=folder/'cases'/c['id']/'inputs'
            if noise:assert noise_spec in (inputs/c['sources']['entry']).read_text()
            sources={name:(inputs/name).read_text() for name in c['sources']['sources'] if name!=c['sources']['entry']}
            if reference_sources is None:reference_sources=sources
            else:source_equal=source_equal and sources==reference_sources
            noise_actual={}
            if noise:
                log=(folder/'cases'/c['id']/'logs/spectre.log').read_text(errors='replace')
                for parameter in ('noisefmin','noisefmax'):
                    match=re.search(r'^\s*'+parameter+r'\s*=\s*([\d.eE+-]+)\s+(Hz|kHz|MHz|GHz)\s*$',log,re.M)
                    assert match,('Missing actual transient-noise setting',parameter,c['id'])
                    noise_actual[parameter+'_hz']=float(match[1])*{'Hz':1,'kHz':1e3,'MHz':1e6,'GHz':1e9}[match[2]]
            rows.append(dict(batch=folder.name,case=c['id'],corner=key[0],temp_c=key[1],noise=noise,k=k,noise_actual=noise_actual,
                passed=bool(result.get('pass')),execution_pass=result.get('execution_pass'),
                metrics=result.get('metrics',{}),power=result.get('power',{}),
                failed_checks=[name for name,value in result.get('checks',{}).items() if not value]))
    expected={(c,t,n,k) for c,t in [('tt',25),('ss',-40),('ss',125),('ff',-40),('ff',125)] for n in (False,True) for k in (3,51)}
    assert seen<=expected,('Unexpected formal conditions',seen-expected)
    complete=seen==expected and source_equal and all(r['passed'] for r in rows)
    report=dict(all_electrical_pass=complete,dut_sources_equal=source_equal,cell_views=final['cell_views'],required_cases=20,
        completed_cases=len(rows),passed_cases=sum(r['passed'] for r in rows),
        batches=[str(p.resolve()) for p in a.batches],cases=rows,
        missing_cases=[list(k) for k in sorted(expected-seen)])
    write_json(ROOT/'config/acceptance_results.json',report)
    final['status']='electrical_pass_oa_pending' if complete else 'electrical_acceptance_incomplete'
    write_json(ROOT/'config/final_design.json',final)
    lines=['---','title: 晶体管 ADC 正式电气验收','type: verification-method','status: active',
        'last_reviewed: 2026-10-23','authoritative_sources:',
        '  - ../../config/acceptance_results.json','  - ../../config/final_design.json','---','',
        '# 晶体管 ADC 正式电气验收','',
        f'同一 DUT 已完成 {len(rows)}/20 个 case，其中 {report["passed_cases"]} 个通过。'+('全部电气验收通过，可进入 OA 收尾。' if complete else '尚未完成全部电气验收。'),'',
        '各批次的 DUT 源文件一致性：'+('通过。' if source_equal else '失败，不能合并为同一版本。'),'',
        '固定方法见 [验收与功耗测量](acceptance-method.md)。每项使用丢弃 16 周期后的连续 256 个实际输出码；含噪声请求 1 Hz–50 GHz、seed=1。Spectre 19.1 将下限自动设为 1/5.8 µs，实际约 172.414 kHz；上限保持 50 GHz。','',
        '| 工艺 | 温度 °C | 噪声 | k | SNDR dB | EOC 最小余量 ns | 逐位 RMS mV | 通过 |',
        '|---|---:|---|---:|---:|---:|---:|---|']
    def value(obj,key,scale=1):
        return f'{obj[key]*scale:.3f}' if obj.get(key) is not None else '—'
    for r in rows:
        m=r['metrics'];lines.append(f'| {r["corner"].upper()} | {r["temp_c"]} | {"开启" if r["noise"] else "关闭"} | {r["k"]} | {value(m,"sndr_db")} | {value(m,"timing_margin_min_s",1e9)} | {value(m,"step_diff_error_rms_v",1e3)} | {"是" if r["passed"] else "否："+", ".join(r["failed_checks"])} |')
    lines+=['','## 稳态功耗','',
        '功率正值表示电源向电路供能。总供电包含 VDD、VREFP 和 VCM；输出缓冲已经包含在 VDD 中。主时钟输入能量单列。', '',
        '| 工艺/温度 | 噪声 | k | VDD mW | VREFP mW | VCM mW | 输出缓冲 mW | 含缓冲总供电 mW | 时钟输入 mW |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        q=r['power'];v=[value(q,key,1e3) for key in ('VDD_w','VREFP_w','VCM_w','output_buffers_w','total_with_buffers_w','clock_input_w')]
        lines.append('| '+f'{r["corner"].upper()}/{r["temp_c"]} | {"开启" if r["noise"] else "关闭"} | {r["k"]} | '+' | '.join(v)+' |')
    lines+=['','## 复查入口','',
        '`config/final_design.json` 固定模块绑定与 flow；`config/acceptance_results.json` 保存逐项指标、失败项及批次路径。',
        '每批 `summary.json`、`cases/*/results.json` 和完整日志保留实际码、逐位轨迹、频谱、功耗及执行状态。',
        '256 点、单种子噪声结果只说明该次仿真表现；本任务未实施失配 Monte Carlo 或良率分析。','']
    (ROOT/'docs/verification/electrical-acceptance.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({key:report[key] for key in ('all_electrical_pass','dut_sources_equal','completed_cases','passed_cases')}))


if __name__ == "__main__":
    main()
