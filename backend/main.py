from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    desc: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/")
def creat_item(item: Item):
    return {"Item created" : item}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}