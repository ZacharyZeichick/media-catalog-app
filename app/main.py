from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import engine
from app.models import catalog  # noqa: F401 — registers models with Base
from app.routers import catalog as catalog_router
from app.routers import lists as lists_router
from app.routers import recommend as recommend_router
from app.routers import watchlist as watchlist_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no-op if they already exist)
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Movie Catalog", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


app.include_router(catalog_router.router, prefix="/api")
app.include_router(lists_router.router, prefix="/api")
app.include_router(recommend_router.router, prefix="/api")
app.include_router(watchlist_router.router, prefix="/api")
# app.include_router(dashboard.router, prefix="/api")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
