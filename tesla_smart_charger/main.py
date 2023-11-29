"""
Tesla smart car charger

This script is the main entry point for the Tesla smart car charger.
"""


from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
