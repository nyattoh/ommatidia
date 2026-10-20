import os
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import fitz
import pytest


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'paper/minimal-protocol'


def run(script, paper, epoch=None, optimised=False):
    env = os.environ.copy()
    env.pop('SOURCE_DATE_EPOCH', None)
    if epoch is not None:
        env['SOURCE_DATE_EPOCH'] = epoch
    return subprocess.run([sys.executable, *(['-O'] if optimised else []), '-B', str(paper/script)], env=env,
                          capture_output=True, text=True, encoding='utf-8')


def copy_paper(tmp_path):
    paper = tmp_path/'paper/minimal-protocol'
    shutil.copytree(PAPER, paper, ignore=shutil.ignore_patterns('rendered', 'zenodo-metadata.md'))
    (tmp_path/'articles').mkdir()
    shutil.copy2(ROOT/'articles/ommatidia-design-plan.md', tmp_path/'articles/ommatidia-design-plan.md')
    return paper


@pytest.mark.parametrize('epoch,expected_date', [(None, 'D:20261021000000'), ('1700000000', 'D:20231114221320')])
def test_pdf_and_checksums_are_reproducible(tmp_path, epoch, expected_date):
    paper = copy_paper(tmp_path)
    first = run('build.py', paper, epoch)
    assert first.returncode == 0, first.stdout+first.stderr
    before = {name: (paper/name).read_bytes() for name in ('manuscript.pdf', 'SHA256SUMS.txt')}
    time.sleep(1.1)
    second = run('build.py', paper, epoch)
    assert second.returncode == 0, second.stdout+second.stderr
    assert before == {name: (paper/name).read_bytes() for name in before}, 'Consecutive PDF/checksum bytes differ'
    with fitz.open(paper/'manuscript.pdf') as doc:
        assert doc.metadata['creationDate'].startswith(expected_date)
        assert doc.metadata['modDate'].startswith(expected_date)


@pytest.fixture
def built_paper(tmp_path):
    paper = copy_paper(tmp_path)
    result = run('build.py', paper)
    assert result.returncode == 0, result.stdout+result.stderr
    return paper


@pytest.mark.parametrize('case', ['missing', 'empty', 'source_only', 'pdf_only', 'duplicate', 'unexpected'])
def test_verify_rejects_incomplete_or_ambiguous_checksums(built_paper, case):
    file = built_paper/'SHA256SUMS.txt'
    lines = file.read_text(encoding='utf-8').splitlines()
    if case == 'missing':
        file.unlink()
    else:
        rows = {'empty': [], 'source_only': lines[:1], 'pdf_only': lines[1:],
                'duplicate': lines+[lines[0]], 'unexpected': lines+[lines[0].replace('manuscript.md', '../manuscript.md')]}[case]
        file.write_text('\n'.join(rows)+('\n' if rows else ''), encoding='utf-8')
    result = run('verify.py', built_paper)
    assert result.returncode != 0, result.stdout+result.stderr


def test_valid_checksums_and_licence_are_accepted(built_paper):
    result = run('verify.py', built_paper)
    assert result.returncode == 0, result.stdout+result.stderr
    metadata = (built_paper/'zenodo-metadata.md').read_text(encoding='utf-8')
    manuscript = (built_paper/'manuscript.md').read_text(encoding='utf-8')
    assert 'CC-BY-4.0' in metadata and 'https://creativecommons.org/licenses/by/4.0/' in metadata
    assert 'CC-BY-4.0' in manuscript
    article = (built_paper.parents[1]/'articles/ommatidia-design-plan.md').read_text(encoding='utf-8')
    assert 'CC-BY-4.0' in article and '\npublished: false\n' in article


def test_verify_rejects_wrong_digest(built_paper):
    file = built_paper/'SHA256SUMS.txt'
    lines = file.read_text(encoding='utf-8').splitlines()
    lines[0] = '0'*64+'  manuscript.md'
    file.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    assert run('verify.py', built_paper).returncode != 0


def test_generated_publication_text_uses_lf_bytes(built_paper):
    result = run('verify.py', built_paper)
    assert result.returncode == 0, result.stdout+result.stderr
    for name in ('SHA256SUMS.txt', 'zenodo-metadata.md', 'validation.json'):
        data = (built_paper/name).read_bytes()
        assert b'\r' not in data, name+' contains CR bytes that Git would normalise'
        assert data.endswith(b'\n'), name+' must end with LF'


def test_reproducibility_receipts_match_canonical_checkout_bytes(tmp_path):
    paper = copy_paper(tmp_path)
    result = run('check_reproducibility.py', paper)
    assert result.returncode == 0, result.stdout+result.stderr
    receipt_bytes = (paper/'reproducibility.json').read_bytes()
    assert b'\r' not in receipt_bytes
    records = json.loads(receipt_bytes)
    for mode in ('default', 'explicit'):
        assert records[mode]['byteIdentical'] is True
        assert records[mode]['runs'][0]['hashes'] == records[mode]['runs'][1]['hashes']
    for name, digest in records['default']['runs'][0]['hashes'].items():
        data = (paper/name).read_bytes()
        if name.endswith('.txt'):
            assert data == data.replace(b'\r\n', b'\n')
        assert hashlib.sha256(data).hexdigest() == digest


@pytest.mark.parametrize('optimised', [False, True])
def test_verify_accepts_valid_inputs_in_both_modes(built_paper, optimised):
    result = run('verify.py', built_paper, optimised=optimised)
    assert result.returncode == 0, result.stdout+result.stderr


@pytest.mark.parametrize('optimised', [False, True])
@pytest.mark.parametrize('case', [
    'source', 'pdf', 'licence', 'licence_link', 'abstract', 'published',
    'missing_manifest', 'empty_manifest', 'partial_manifest', 'digest',
])
def test_verify_rejects_tampering_in_both_modes(built_paper, optimised, case):
    manifest = built_paper/'SHA256SUMS.txt'
    metadata = built_paper/'zenodo-metadata.md'
    if case == 'source':
        source = built_paper/'manuscript.md'
        source.write_text(source.read_text(encoding='utf-8')+'\nUnrendered tampered paragraph.\n', encoding='utf-8', newline='\n')
    elif case == 'pdf':
        pdf = built_paper/'manuscript.pdf'
        with fitz.open(pdf) as doc:
            doc.delete_page(len(doc)-1)
            data = doc.tobytes()
        pdf.write_bytes(data)
    elif case in ('licence', 'licence_link', 'abstract'):
        text = metadata.read_text(encoding='utf-8')
        old = {'licence': 'Creative Commons Attribution 4.0 International (CC-BY-4.0)',
               'licence_link': 'https://creativecommons.org/licenses/by/4.0/',
               'abstract': 'An investigation can end with a fluent answer'}[case]
        assert old in text
        metadata.write_text(text.replace(old, 'Tampered metadata'), encoding='utf-8', newline='\n')
    elif case == 'published':
        article = built_paper.parents[1]/'articles/ommatidia-design-plan.md'
        article.write_text(article.read_text(encoding='utf-8').replace('published: false', 'published: true'), encoding='utf-8', newline='\n')
    elif case == 'missing_manifest':
        manifest.unlink()
    elif case == 'empty_manifest':
        manifest.write_bytes(b'')
    elif case == 'partial_manifest':
        manifest.write_text(manifest.read_text(encoding='utf-8').splitlines()[0]+'\n', encoding='utf-8', newline='\n')
    elif case == 'digest':
        rows = manifest.read_text(encoding='utf-8').splitlines()
        rows[0] = '0'*64+'  manuscript.md'
        manifest.write_text('\n'.join(rows)+'\n', encoding='utf-8', newline='\n')
    if case in ('source', 'pdf'):
        # Keep hashes valid so this tests the semantic checks, not checksum failure.
        manifest.write_text(''.join(hashlib.sha256((built_paper/name).read_bytes()).hexdigest()+'  '+name+'\n'
                                    for name in ('manuscript.md', 'manuscript.pdf')), encoding='utf-8', newline='\n')
    result = run('verify.py', built_paper, optimised=optimised)
    assert result.returncode != 0, case+' was accepted: '+result.stdout+result.stderr
