import os
import re

from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

from app.celery_app import celery_app
from app.tasks import generate_ebook

app = FastAPI(title="Inkbind API", version="0.1.0")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")
FILE_ID_PATTERN = re.compile(r"^ebook_[a-f0-9-]{16,64}\.pdf$")
TASK_ID_PATTERN = re.compile(r"^[a-f0-9-]{16,64}$")


class ConvertRequest(BaseModel):
    url: HttpUrl


@app.get("/health")
def health():
    return {"status": "ok", "service": "inkbind-api"}


@app.post("/convert", status_code=202)
def convert_blog(req: ConvertRequest):
    task = generate_ebook.delay(str(req.url))
    return {"task_id": task.id, "status": "queued"}


@app.get("/status/{task_id}")
def get_status(task_id: str):
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise HTTPException(status_code=400, detail="task_id inválido")
    task_result = AsyncResult(task_id, app=celery_app)
    status = task_result.status
    response = {"task_id": task_id, "status": status}
    if status == "PROGRESS":
        info = task_result.info
        response["meta"] = info if isinstance(info, dict) else {}
    elif status == "SUCCESS":
        result = task_result.result
        if isinstance(result, dict):
            response["result"] = result
    elif status == "FAILURE":
        response["error"] = "A conversão falhou. Verifique a URL e tente novamente."
    return response


@app.get("/download/{file_id}")
def download_ebook(file_id: str):
    if not FILE_ID_PATTERN.fullmatch(file_id):
        raise HTTPException(status_code=400, detail="file_id inválido")
    file_path = os.path.join(STORAGE_DIR, file_id)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path=file_path, media_type="application/pdf", filename=file_id)
