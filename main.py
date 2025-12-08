import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from lifespan import lifespan
from api import auth, dialogs, messages, events, files, user, logout

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Telethon Web-Client",
    version="0.1.0",
    lifespan=lifespan
)

for r in [auth, dialogs, messages, events, files, user, logout]:
    app.include_router(r.router)


templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
