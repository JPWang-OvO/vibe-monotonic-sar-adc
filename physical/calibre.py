"""Run the Calibre portion of a project job in the Calibre Bridge environment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

from calibre_bridge import CalibreClient
from calibre_bridge.client import LaunchUncertainError
from calibre_bridge.models import JobRequest

from regression.common.project import read_json, write_json


def operate(action, folder, operation=None):
    folder = Path(folder)
    run = read_json(folder / 'run.json')
    config = run['environment']['calibre']
    if action == 'validate':
        for name in run['target']['operations']:
            JobRequest.model_validate(read_json(folder / f'{name}.request.json'))
        return {'validated': run['target']['operations']}

    with CalibreClient.from_config(config['config'], profile=config['profile']) as client:
        client.profile = client.profile.model_copy(update={'runs_root': run['remote'] + '/jobs'})
        if action == 'stage':
            result = client.stage_technology(run['remote'] + '/technology')
            write_json(folder / 'technology.json', result)
            return result

        receipt = folder / f'{operation}.submission.json'
        if action == 'submit':
            if receipt.exists():
                raise FileExistsError(f'Job already recorded in {receipt}; query that run_id')
            request = read_json(folder / f'{operation}.request.json')
            try:
                result = client.run(request)
            except LaunchUncertainError as error:
                write_json(receipt, {'run_id': error.run_id, 'run_dir': error.run_dir,
                                     'acknowledgement': 'uncertain'})
                raise
            write_json(receipt, result)
            return result

        run_id = read_json(receipt)['run_id']
        if action == 'status':
            return client.status(run_id)
        if action == 'cancel':
            return client.cancel(run_id)

        report = client.report(run_id, limit=1000)
        if report['available']:
            items = report['diagnostics']['items']
            while report['diagnostics']['has_more']:
                page = client.report(run_id, offset=len(items), limit=1000)
                items.extend(page['diagnostics']['items'])
                report['diagnostics']['has_more'] = page['diagnostics']['has_more']
            report['diagnostics']['limit'] = len(items)
            logs = folder / operation
            logs.mkdir(exist_ok=True)
            client.transport.sftp.get(report['run']['run_dir'] + '/transcript.log', str(logs / 'transcript.log'))
            extraction = report.get('extraction', {})
            if extraction.get('generated'):
                remote_root = PurePosixPath(extraction['files'][0]['path']).parent
                for source in extraction['files']:
                    relative = PurePosixPath(source['path']).relative_to(remote_root)
                    local = folder / 'extracted' / relative.as_posix()
                    local.parent.mkdir(parents=True, exist_ok=True)
                    client.transport.sftp.get(source['path'], str(local))
        write_json(folder / f'{operation}.report.json', report)
        return {key: report[key] for key in ('run', 'available', 'parser_status', 'verification', 'extraction') if key in report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('validate', 'stage', 'submit', 'status', 'collect', 'cancel'))
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--operation', choices=('drc', 'lvs', 'pex'))
    args = parser.parse_args()
    print(json.dumps(operate(args.action, args.run, args.operation), ensure_ascii=False))


if __name__ == '__main__':
    main()
