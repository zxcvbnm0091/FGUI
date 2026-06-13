from sqlmodel import create_engine, Session, text
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
database_filename = BASE_DIR / "data" / "games.db"
database_url = f"sqlite:///{database_filename}"

engine = create_engine(database_url, connect_args={"check_same_thread": False})

with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))

def get_session():
    with Session(engine) as session:
        yield session