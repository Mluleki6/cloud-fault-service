"""
Test bootstrap.

Points DATABASE_URL at a scratch SQLite file *before* app.persistence is
imported anywhere, so the whole test session runs against an isolated
database rather than whatever a developer has configured locally.
"""
import os
import sys
import tempfile

_tmp_dir = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_dir}/test_fault_service.db")
os.environ.setdefault("NOTIFY_FORCE_FAILURE", "0")
os.environ.setdefault("DB_FORCE_FAILURE", "0")

# Make sure the project root (parent of tests/) is importable as "app.*"
# regardless of how pytest was invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.persistence import Base, engine


@pytest.fixture(autouse=True)
def _clean_db():
    """Give every test a clean set of tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
