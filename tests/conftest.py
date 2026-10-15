"""All tests reject private dataset access, including accidental fixture reads."""

import builtins
import io
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def reject_private_dataset_io(monkeypatch):
    def guard(function):
        def checked(path, *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)):
                value = Path(os.fsdecode(path))
                if value.name == "unblinding_key.json" or any(part.lower() in ("gold", "cases") for part in value.parts):
                    raise AssertionError("Tests must not access private evaluation files")
            return function(path, *args, **kwargs)
        return checked
    monkeypatch.setattr(builtins, "open", guard(builtins.open))
    monkeypatch.setattr(io, "open", guard(io.open))
    monkeypatch.setattr(os, "open", guard(os.open))
