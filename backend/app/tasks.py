import os

from app.builder import build_pdf
from app.celery_app import celery_app
from app.scraper import scrape_post

STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")


@celery_app.task(bind=True)
def generate_ebook(self, url: str):
    self.update_state(state="PROGRESS", meta={"step": "scraping"})
    post_data = scrape_post(url)
    self.update_state(state="PROGRESS", meta={"step": "building_pdf"})
    os.makedirs(STORAGE_DIR, exist_ok=True)
    file_id = f"ebook_{self.request.id}.pdf"
    output_path = os.path.join(STORAGE_DIR, file_id)
    build_pdf(post_data, output_path)
    return {"status": "done", "file_id": file_id, "title": post_data["title"]}
