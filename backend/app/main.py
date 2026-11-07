import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import projects, companies, terms, founders, risks, documents, summary

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Система кредитного анализа групп компаний",
    description="Внутренняя система подготовки резюме по проектам финансирования: "
                "отчетность, коэффициенты, NPV/IRR/DSCR, проверки учредителей, скоринг, резюме.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(companies.router)
app.include_router(terms.router)
app.include_router(founders.router)
app.include_router(risks.router)
app.include_router(documents.router)
app.include_router(summary.router)


@app.get("/api/health", summary="Проверка работоспособности")
def health():
    return {"status": "ok", "service": "credit-analysis"}


# Production: backend раздает собранный фронтенд
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        index = os.path.join(FRONTEND_DIST, "index.html")
        target = os.path.join(FRONTEND_DIST, full_path) if full_path else index
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(index)
