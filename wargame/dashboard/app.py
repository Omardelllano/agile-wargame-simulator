from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from wargame.dashboard.routes.reports import router as reports_router
from wargame.dashboard.routes.simulate import router as simulate_router

_HERE = Path(__file__).parent

app = FastAPI(title="Agile Wargame Simulator", version="0.1.0")

app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(_HERE / "templates"))

app.include_router(simulate_router)
app.include_router(reports_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
