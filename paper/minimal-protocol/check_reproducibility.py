"""Rebuild both timestamp modes twice and save LF-byte reproducibility receipts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import fitz

paper = Path(__file__).resolve().parent
records = {}
for label, value in [('default', None), ('explicit', '1700000000')]:
    runs, snapshots = [], []
    for i in range(2):
        env = os.environ.copy()
        env.pop('SOURCE_DATE_EPOCH', None)
        if value is not None:
            env['SOURCE_DATE_EPOCH'] = value
        result = subprocess.run([sys.executable, '-B', str(paper/'build.py')], env=env, capture_output=True)
        if result.returncode:
            sys.stdout.buffer.write(result.stdout+result.stderr)
            raise SystemExit(result.returncode)
        snapshot = {name: (paper/name).read_bytes() for name in ['manuscript.pdf', 'SHA256SUMS.txt']}
        if b'\r' in snapshot['SHA256SUMS.txt']:
            raise ValueError('SHA256SUMS.txt contains non-canonical CR bytes')
        snapshots.append(snapshot)
        with fitz.open(paper/'manuscript.pdf') as doc:
            dates = {k: doc.metadata[k] for k in ['creationDate', 'modDate']}
        runs.append({'run': i+1, 'hashes': {k: hashlib.sha256(v).hexdigest() for k, v in snapshot.items()}, 'dates': dates, 'exitCode': 0})
        if i == 0:
            time.sleep(1.1)
    if snapshots[0] != snapshots[1]:
        raise ValueError('Consecutive PDF/checksum bytes differ: '+label)
    records[label] = {'SOURCE_DATE_EPOCH': value, 'byteIdentical': True, 'runs': runs}

env = os.environ.copy()
env.pop('SOURCE_DATE_EPOCH', None)
subprocess.run([sys.executable, '-B', str(paper/'build.py')], env=env, check=True, capture_output=True)
for name, digest in records['default']['runs'][0]['hashes'].items():
    if hashlib.sha256((paper/name).read_bytes()).hexdigest() != digest:
        raise ValueError('Final default artefact differs from receipt: '+name)
(paper/'reproducibility.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8', newline='\n')
print(json.dumps(records, indent=2))
