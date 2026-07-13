import os
import sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure testing mode is enabled before importing anything from the app
os.environ["TESTING"] = "true"

from sqlmodel import Session, SQLModel
from app.database.engine import engine

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    with Session(engine) as session:
        yield session
