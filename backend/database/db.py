from sqlmodel import create_engine, Session


database_filename="../data/game.db"
database_url = f"sqlite:///{database_filename}"

engine = create_engine(database_url)

def get_session():
    with Session(engine) as session:
        yield session