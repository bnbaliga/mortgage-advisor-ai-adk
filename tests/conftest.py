"""Shared test setup.

Runtime databases go to a temporary folder so tests never touch data/mortgage/.
This runs before any test module imports mortgage_advisor (config reads the
environment once, at import).
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="mortgage-tests-")
os.environ.setdefault("MORTGAGE_SERVICING_DB", os.path.join(_TMP, "servicing.db"))
os.environ.setdefault("MORTGAGE_KNOWLEDGE_DB", os.path.join(_TMP, "passages.db"))
os.environ.setdefault("MORTGAGE_GREETING", "0")
