from sqlmodel import create_engine

database_filename="../data/game.db"
database_url = f"sqlite:///{database_filename}"

engine = create_engine(database_url)