import os
import hashlib
import json
import contextlib
import io
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time

import pytest

for optional_dependency in ('fitz', 'markdown_it', 'reportlab', 'matplotlib', 'PIL'):
    pytest.importorskip(optional_dependency)

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
    fitz = pytest.importorskip('fitz')
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


@pytest.mark.parametrize('epoch', [None, '01700000000'])
def test_build_preserves_process_source_date_epoch_and_is_reproducible(tmp_path, monkeypatch, epoch):
    paper = copy_paper(tmp_path)
    monkeypatch.chdir(paper)
    expected_env = epoch
    if epoch is None:
        monkeypatch.delenv('SOURCE_DATE_EPOCH', raising=False)
    else:
        monkeypatch.setenv('SOURCE_DATE_EPOCH', epoch)

    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(str(paper/'build.py'), run_name='__main__')
    first = {name: (paper/name).read_bytes() for name in ('manuscript.pdf', 'SHA256SUMS.txt')}
    assert os.environ.get('SOURCE_DATE_EPOCH') == expected_env

    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(str(paper/'build.py'), run_name='__main__')
    second = {name: (paper/name).read_bytes() for name in first}
    assert os.environ.get('SOURCE_DATE_EPOCH') == expected_env
    assert first == second, 'Consecutive PDF/checksum bytes differ in a long-lived process'


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


@pytest.mark.parametrize('optimised', [False, True])
@pytest.mark.parametrize('field', [
    'title', 'creator_family_name', 'creator_given_name', 'creator_orcid', 'language',
])
def test_verify_rejects_missing_approved_zenodo_metadata_without_writing_validation(
        built_paper, optimised, field):
    metadata = built_paper/'zenodo-metadata.md'
    validation = built_paper/'validation.json'
    validation_before = validation.read_bytes()
    title = (built_paper/'manuscript.md').read_text(encoding='utf-8').splitlines()[0].removeprefix('# ')
    approved, diagnostic = {
        'title': (title, 'Zenodo metadata is missing the approved title'),
        'creator_family_name': ('Family name: Sakakibara', 'Zenodo metadata is missing the approved creator family name'),
        'creator_given_name': ('Given name: Ryoko', 'Zenodo metadata is missing the approved creator given name'),
        'creator_orcid': ('ORCID: 0009-0009-9544-6315', 'Zenodo metadata is missing the approved creator ORCID'),
        'language': ('English (eng)', 'Zenodo metadata is missing the approved language'),
    }[field]
    text = metadata.read_text(encoding='utf-8')
    assert approved in text
    metadata.write_text(text.replace(approved, 'Removed approved metadata field', 1), encoding='utf-8', newline='\n')

    result = run('verify.py', built_paper, optimised=optimised)
    assert result.returncode != 0, result.stdout+result.stderr
    assert diagnostic in result.stderr
    assert validation.read_bytes() == validation_before, 'Rejected metadata changed validation.json'


@pytest.mark.parametrize('optimised', [False, True])
@pytest.mark.parametrize(('surface', 'omission'), [
    ('article', 'name'), ('article', 'identifier'), ('article', 'url'),
    ('manuscript', 'name'), ('manuscript', 'identifier'), ('manuscript', 'url'),
])
def test_verify_rejects_missing_publication_licence_fields_without_writing_validation(
        built_paper, optimised, surface, omission):
    validation = built_paper/'validation.json'
    validation_before = validation.read_bytes()
    if surface == 'article':
        file = built_paper.parents[1]/'articles/ommatidia-design-plan.md'
        assert '\npublished: false\n' in file.read_text(encoding='utf-8')
        approved = {
            'name': 'Creative Commons Attribution 4.0 International',
            'identifier': 'CC-BY-4.0',
            'url': 'https://creativecommons.org/licenses/by/4.0/',
        }[omission]
    else:
        file = built_paper/'manuscript.md'
        approved = {
            'name': 'Creative Commons Attribution 4.0 International',
            'identifier': 'CC-BY-4.0',
            'url': 'https://creativecommons.org/licenses/by/4.0/',
        }[omission]
    text = file.read_text(encoding='utf-8')
    assert approved in text
    file.write_text(text.replace(approved, 'Removed approved licence field', 1), encoding='utf-8', newline='\n')
    if surface == 'manuscript':
        build_result = run('build.py', built_paper)
        assert build_result.returncode == 0, build_result.stdout+build_result.stderr

    result = run('verify.py', built_paper, optimised=optimised)
    assert result.returncode != 0, result.stdout+result.stderr
    assert f'The {surface} is missing the approved licence {omission}' in result.stderr
    assert validation.read_bytes() == validation_before, 'Rejected licence changed validation.json'


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


def test_committed_current_byte_hash_claims_match_generated_artifacts():
    """Current receipts and validation metadata must identify the checked-in bytes."""
    raw = {
        name: hashlib.sha256((PAPER/name).read_bytes()).hexdigest()
        for name in ('manuscript.md', 'manuscript.pdf')
    }
    validation = json.loads((PAPER/'validation.json').read_text(encoding='utf-8'))
    checksums = (PAPER/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines()
    entries = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in checksums}
    assert entries == raw
    assert validation['sourceSha256'] == raw['manuscript.md']
    assert validation['pdfSha256'] == raw['manuscript.pdf']

    records = json.loads((PAPER/'reproducibility.json').read_text(encoding='utf-8'))
    default = records['default']['runs'][0]['hashes']
    assert default['manuscript.pdf'] == raw['manuscript.pdf']
    assert default['SHA256SUMS.txt'] == hashlib.sha256((PAPER/'SHA256SUMS.txt').read_bytes()).hexdigest()


@pytest.mark.parametrize('optimised', [False, True])
def test_verify_accepts_valid_inputs_in_both_modes(built_paper, optimised):
    result = run('verify.py', built_paper, optimised=optimised)
    assert result.returncode == 0, result.stdout+result.stderr


@pytest.mark.parametrize('optimised', [False, True])
@pytest.mark.parametrize('case', [
    'source', 'pdf', 'pdf_added_paragraph', 'licence', 'licence_link', 'abstract', 'published',
    'missing_manifest', 'empty_manifest', 'partial_manifest', 'digest',
])
def test_verify_rejects_tampering_in_both_modes(built_paper, optimised, case):
    manifest = built_paper/'SHA256SUMS.txt'
    metadata = built_paper/'zenodo-metadata.md'
    validation = built_paper/'validation.json'
    validation_before = validation.read_bytes() if case == 'pdf_added_paragraph' else None
    if case == 'source':
        source = built_paper/'manuscript.md'
        source.write_text(source.read_text(encoding='utf-8')+'\nUnrendered tampered paragraph.\n', encoding='utf-8', newline='\n')
    elif case == 'pdf':
        fitz = pytest.importorskip('fitz')
        pdf = built_paper/'manuscript.pdf'
        with fitz.open(pdf) as doc:
            doc.delete_page(len(doc)-1)
            data = doc.tobytes()
        pdf.write_bytes(data)
    elif case == 'pdf_added_paragraph':
        fitz = pytest.importorskip('fitz')
        pdf = built_paper/'manuscript.pdf'
        with fitz.open(pdf) as doc:
            # Keep the added paragraph fully inside page 1 and outside the footer.
            doc[0].insert_text((72, 720), 'Added paragraph: a new result was observed.', fontsize=9)
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
    if case in ('source', 'pdf', 'pdf_added_paragraph'):
        # Keep hashes valid so this tests the semantic checks, not checksum failure.
        manifest.write_text(''.join(hashlib.sha256((built_paper/name).read_bytes()).hexdigest()+'  '+name+'\n'
                                    for name in ('manuscript.md', 'manuscript.pdf')), encoding='utf-8', newline='\n')
    result = run('verify.py', built_paper, optimised=optimised)
    assert result.returncode != 0, case+' was accepted: '+result.stdout+result.stderr
    if case == 'pdf_added_paragraph':
        assert validation.read_bytes() == validation_before, 'Rejected PDF changed validation.json'


def test_build_preserves_reportlab_invariant_after_success(tmp_path, monkeypatch):
    from reportlab import rl_config

    paper = copy_paper(tmp_path)
    monkeypatch.chdir(paper)
    expected = 37
    monkeypatch.setattr(rl_config, 'invariant', expected)

    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(str(paper/'build.py'), run_name='__main__')

    assert rl_config.invariant == expected


def test_build_preserves_reportlab_invariant_after_failure(tmp_path, monkeypatch):
    from reportlab import rl_config

    paper = copy_paper(tmp_path)
    monkeypatch.chdir(paper)
    expected = 41
    monkeypatch.setattr(rl_config, 'invariant', expected)
    original_read_text = Path.read_text

    def fail_on_manuscript(path, *args, **kwargs):
        if path == paper/'manuscript.md':
            raise OSError('forced manuscript read failure')
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', fail_on_manuscript)
    with contextlib.redirect_stdout(io.StringIO()), pytest.raises(OSError, match='forced manuscript read failure'):
        runpy.run_path(str(paper/'build.py'), run_name='__main__')

    assert rl_config.invariant == expected


def _reportlab_font_registry_state():
    from reportlab.lib import fonts
    from reportlab.pdfbase import pdfmetrics

    registries = {
        'fonts': pdfmetrics._fonts,
        'dynamic_face_names': pdfmetrics._dynFaceNames,
        'typeface_to_postscript': fonts._tt2ps_map,
        'postscript_to_typeface': fonts._ps2tt_map,
    }
    return {name: registry.copy() for name, registry in registries.items()}


def _restore_reportlab_font_registry_state(state):
    from reportlab.lib import fonts
    from reportlab.pdfbase import pdfmetrics

    registries = {
        'fonts': pdfmetrics._fonts,
        'dynamic_face_names': pdfmetrics._dynFaceNames,
        'typeface_to_postscript': fonts._tt2ps_map,
        'postscript_to_typeface': fonts._ps2tt_map,
    }
    for name, registry in registries.items():
        registry.clear()
        registry.update(state[name])


def _reportlab_font_registry_changes(before, after):
    old = _reportlab_font_registry_signature(before)
    new = _reportlab_font_registry_signature(after)
    return {name: {'before': old[name], 'after': new[name]}
            for name in old if old[name] != new[name]}


def _reportlab_font_registry_signature(state):
    font_names = ('Body', 'Bold', 'Italic')
    family_keys = {('body', bold, italic) for bold in (0, 1) for italic in (0, 1)}
    postscript_names = {'body', 'bold', 'italic'}
    return {
        'fonts': {name: _reportlab_registry_value(state['fonts'][name])
                  for name in font_names if name in state['fonts']},
        'dynamic_face_names': {name: _reportlab_registry_value(value)
                               for name, value in state['dynamic_face_names'].items()},
        'typeface_to_postscript': {key: state['typeface_to_postscript'][key]
                                   for key in family_keys if key in state['typeface_to_postscript']},
        'postscript_to_typeface': {name: state['postscript_to_typeface'][name]
                                   for name in postscript_names if name in state['postscript_to_typeface']},
    }


def _reportlab_registry_value(value):
    if hasattr(value, 'fontName'):
        return (type(value).__name__, value.fontName, id(value))
    return value


def test_build_restores_reportlab_font_registries_after_success(tmp_path, monkeypatch):
    before = _reportlab_font_registry_state()
    paper = copy_paper(tmp_path)
    monkeypatch.chdir(paper)

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(paper/'build.py'), run_name='__main__')
        after = _reportlab_font_registry_state()
        assert _reportlab_font_registry_signature(after) == _reportlab_font_registry_signature(before), \
            _reportlab_font_registry_changes(before, after)
    finally:
        _restore_reportlab_font_registry_state(before)


def test_build_restores_reportlab_font_registries_after_failure(tmp_path, monkeypatch):
    from reportlab.platypus import SimpleDocTemplate

    before = _reportlab_font_registry_state()
    paper = copy_paper(tmp_path)
    monkeypatch.chdir(paper)

    def fail_after_font_registration(*args, **kwargs):
        raise RuntimeError('forced failure after font registration')

    monkeypatch.setattr(SimpleDocTemplate, 'build', fail_after_font_registration)
    try:
        with contextlib.redirect_stdout(io.StringIO()), pytest.raises(
                RuntimeError, match='forced failure after font registration'):
            runpy.run_path(str(paper/'build.py'), run_name='__main__')
        after = _reportlab_font_registry_state()
        assert _reportlab_font_registry_signature(after) == _reportlab_font_registry_signature(before), \
            _reportlab_font_registry_changes(before, after)
    finally:
        _restore_reportlab_font_registry_state(before)
