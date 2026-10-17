"""All tests reject private dataset access, including accidental fixture reads."""

import builtins
import io
import os
from pathlib import Path
import tempfile

import pytest


@pytest.fixture(autouse=True)
def reject_private_dataset_io(monkeypatch, request):
    synthetic_root = None
    if "synthetic_private_io_root" in request.fixturenames:
        synthetic_root = request.getfixturevalue("synthetic_private_io_root")

    def guard(function):
        def checked(path, *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)):
                value = Path(os.fsdecode(path))
                resolved = value.resolve()
                is_key = (
                    value.name == "unblinding_key.json"
                    or resolved.name == "unblinding_key.json"
                )
                is_private = any(
                    part.lower() in ("gold", "cases")
                    for part in (*value.parts, *resolved.parts)
                )
                synthetic = (
                    synthetic_root is not None
                    and value.absolute().is_relative_to(synthetic_root)
                    and resolved.is_relative_to(synthetic_root)
                )
                if is_key or (is_private and not synthetic):
                    raise AssertionError(
                        "Tests must not access private evaluation files"
                    )
            return function(path, *args, **kwargs)

        return checked

    monkeypatch.setattr(builtins, "open", guard(builtins.open))
    monkeypatch.setattr(io, "open", guard(io.open))
    monkeypatch.setattr(os, "open", guard(os.open))


@pytest.fixture
def synthetic_private_io_root(tmp_path):
    """Opt in to synthetic gold/cases IO inside this test's temporary root only."""
    root = tmp_path.resolve()
    repository = Path(__file__).resolve().parents[1]
    assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert not root.is_relative_to(repository)
    assert not repository.is_relative_to(root)
    return root
