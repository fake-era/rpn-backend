from pydantic import constr
from starlette.middleware.cors import CORSMiddleware
import uvicorn
from celery.result import AsyncResult
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import JSONResponse
from schemas import Task as SchemaTask
from schemas import Result as SchemaResult
from models import Task as ModelTask
from models import Result as ModelResult
import os
from base import Session, engine, Base
from worker import create_task, update_data

Base.metadata.create_all(engine)

session = Session()

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"by": "yerassyl"}


@app.post("/api/v1/tasks", status_code=201)
async def add_task(payload: SchemaTask):
    task = create_task.delay(payload.iin)
    return JSONResponse({"task_id": task.id})


@app.post("/api/v1/update", status_code=201)
async def update(payload: SchemaTask):
    task = update_data.delay(payload.iin)
    return JSONResponse({"task_id": task.id})


@app.get("/api/v1/tasks/{task_id}")
async def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)


@app.get("/api/v1/persons/{iin}")
async def get_person(iin: constr(min_length=12, max_length=12)):
    db_result = session.query(ModelResult).filter(ModelResult.iin == iin).first()
    try:
        return db_result
    except IndexError:
        session.query(ModelTask).filter(ModelTask.iin == iin). \
            update({'status': 'none'}, synchronize_session="fetch")
        session.commit()
        return 'person not found'


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001)
