from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from db.database import db
from db.queries import (
    get_live_feed,
    get_intervention_history,
    get_server_health_stats,
    get_top_flagged_users,
    get_recent_toxicity_stream,
    get_message_volume,
    get_intervention_breakdown
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="Moderation Dashboard", lifespan=lifespan)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
app.mount("/images", StaticFiles(directory="dashboard/templates/images"), name="images")
templates = Jinja2Templates(directory="dashboard/templates")

# ─── Page Routes (HTML) ───────────────────────────────────────────────────────

@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/monitor")
async def analytics(request: Request):
    return templates.TemplateResponse(request=request, name="monitor.html")

@app.get("/interventions")
async def interventions(request: Request):
    return templates.TemplateResponse(request=request, name="interventions.html")

# ─── API Routes (JSON) ────────────────────────────────────────────────────────

@app.get("/api/{guild_id}/feed")
async def api_feed(guild_id: int):
    rows = await get_live_feed(guild_id, limit=20)
    return jsonable_encoder([dict(r) for r in rows])

@app.get("/api/{guild_id}/toxicity")
async def api_toxicity(guild_id: int):
    rows = await get_recent_toxicity_stream(guild_id, limit=50)
    return jsonable_encoder({"scores": rows})

@app.get("/api/{guild_id}/interventions")
async def api_interventions(guild_id: int):
    rows = await get_intervention_history(guild_id, limit=20)
    return jsonable_encoder([dict(r) for r in rows])

@app.get("/api/{guild_id}/health")
async def api_health(guild_id: int):
    stats = await get_server_health_stats(guild_id)
    return jsonable_encoder({
        "stats": dict(stats) if stats else {},
        "guild_id": guild_id,
    })

@app.get("/api/{guild_id}/top-flagged-users")
async def api_top_flagged_users(guild_id: int):
    flags = await get_top_flagged_users(guild_id)
    return jsonable_encoder({
        "top_flagged_users": [dict(r) for r in flags]
    })

@app.get("/api/{guild_id}/volume")
async def api_volume(guild_id: int):
    rows = await get_message_volume(guild_id, hours=24)
    return jsonable_encoder([dict(r) for r in rows])

@app.get("/api/{guild_id}/breakdown")
async def api_breakdown(guild_id: int):
    rows = await get_intervention_breakdown(guild_id)
    return jsonable_encoder([dict(r) for r in rows])