from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel, Session

from database.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)

app = FastAPI(lifespan=lifespan)

