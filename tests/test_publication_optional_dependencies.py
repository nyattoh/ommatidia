import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_publication_tests_skip_during_collection_without_publication_dependencies(tmp_path):
    blocker = tmp_path / 'sitecustomize.py'
    blocker.write_text(
        '''import importlib.abc\nimport sys\n\nBLOCKED = {"fitz", "markdown_it", "reportlab", "matplotlib", "PIL"}\n\nclass BlockOptionalPublicationDependencies(importlib.abc.MetaPathFinder):\n    def find_spec(self, fullname, path=None, target=None):\n        if fullname.split(".", 1)[0] in BLOCKED:\n            raise ModuleNotFoundError(f"No module named {fullname}", name=fullname)\n\nsys.meta_path.insert(0, BlockOptionalPublicationDependencies())\n''',
        encoding='utf-8',
    )
    blocker_text = blocker.read_text(encoding='utf-8').replace('"PIL"}', '"PIL", "yaml"}')
    blocker.write_text(blocker_text, encoding='utf-8')
    env = os.environ.copy()
    env.pop('SOURCE_DATE_EPOCH', None)
    env['PYTHONPATH'] = str(tmp_path) + os.pathsep + env.get('PYTHONPATH', '')
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            f'import pytest; raise SystemExit(pytest.main(["--collect-only", "-q", "-rs", {str(ROOT / "tests")!r}]))',
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert 'test_publication_build.py' in output and 'SKIPPED' in output, output
