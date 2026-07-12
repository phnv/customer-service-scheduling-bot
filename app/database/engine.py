from sqlmodel import create_engine
import os

# Create SQLite engine
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Set echo=True for debugging if needed
engine = create_engine(sqlite_url, echo=False)
