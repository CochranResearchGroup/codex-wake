"""Opt-in real acquisition with one reply deliberately withheld per control."""
import argparse
import json
from pathlib import Path

from codex_wake.time_inspection import SOURCES, inspect_time, windows_collect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for source in SOURCES:
        if source['scale'] is None:
            continue
        def collect(sources, request):
            data = windows_collect(sources, request)
            data['replies'] = [row for row in data['replies'] if row['host'] != source['host']]
            return data
        report = inspect_time(collector=collect)
        assert report['decision']['status'] == 'network', report
        assert source['host'] not in report['decision']['sources']
        reports.append(dict(withheld_operator=source['operator'],fault='controlled reply omission after real acquisition',report=report))
    args.output.write_text(json.dumps(dict(status='passed',controls=reports),indent=2)+'\n')
    print('Real acquired consensus survives each single-provider omission')


if __name__ == '__main__':
    main()
