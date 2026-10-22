from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import json
import re
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import bcrypt
import jwt
import httpx
import requests
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Form, Depends
from fastapi.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from emergentintegrations.llm.chat import LlmChat, UserMessage

from render import TEMPLATES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
EMERGENT_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
GRAPH = "https://graph.facebook.com/v21.0"
APP_NAME = "newsdesk"

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
storage_key = None

app = FastAPI()
api = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- storage ----------
def init_storage(force=False):
    global storage_key
    if storage_key and not force:
        return storage_key
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    r.raise_for_status()
    storage_key = r.json()["storage_key"]
    return storage_key


def put_object(path, data, content_type):
    r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(), "Content-Type": content_type}, data=data, timeout=120)
    if r.status_code == 404:
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(True), "Content-Type": content_type}, data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def get_object(path):
    r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage()}, timeout=60)
    if r.status_code == 404:
        r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(True)}, timeout=60)
    r.raise_for_status()
    return r.content


async def save_file(data: bytes, ext: str, content_type: str, kind: str) -> str:
    path = f"{APP_NAME}/{kind}/{uuid.uuid4()}.{ext}"
    res = await run_in_threadpool(put_object, path, data, content_type)
    await db.files.insert_one({"storage_path": res["path"], "content_type": content_type, "is_deleted": False, "created_at": now_iso()})
    return res["path"]


def media_url(path, base=""):
    return f"{base}/api/media/{path}"


def public_base(request: Request):
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    return f"https://{host}"


# ---------- auth ----------
def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_pw(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(uid, email, kind, delta):
    return jwt.encode({"sub": uid, "email": email, "type": kind, "exp": datetime.now(timezone.utc) + delta}, JWT_SECRET, algorithm="HS256")


def set_auth_cookies(resp: Response, uid, email):
    resp.set_cookie("access_token", make_token(uid, email, "access", timedelta(hours=12)), httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    resp.set_cookie("refresh_token", make_token(uid, email, "refresh", timedelta(days=7)), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


class LoginIn(BaseModel):
    email: str
    password: str


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5 and att.get("locked_until", "") > now_iso():
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_pw(body.password, user["password_hash"]):
        count = (att or {}).get("count", 0) + 1
        await db.login_attempts.update_one({"identifier": ident}, {"$set": {"count": count, "locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_many({"identifier": ident})
    set_auth_cookies(response, user["id"], email)
    return {"id": user["id"], "email": email, "name": user.get("name"), "role": user.get("role")}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    try:
        payload = jwt.decode(token or "", JWT_SECRET, algorithms=["HS256"])
        assert payload.get("type") == "refresh"
    except Exception:
        raise HTTPException(401, "Invalid refresh token")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    set_auth_cookies(response, user["id"], user["email"])
    return {"ok": True}


# ---------- settings ----------
DEFAULT_SETTINGS = {"brand_name": "ANI", "default_hashtags": "#ANI #news #breakingnews", "default_template": "bw_informative", "default_photo_credit": "ANI Picture Service", "ig_user_id": "", "ig_access_token": ""}


async def get_settings():
    s = await db.settings.find_one({"key": "main"}, {"_id": 0}) or {}
    return {**DEFAULT_SETTINGS, **{k: v for k, v in s.items() if k != "key"}}


class SettingsIn(BaseModel):
    brand_name: str
    default_hashtags: str = ""
    default_template: str = "bw_informative"
    default_photo_credit: str = ""
    ig_user_id: str = ""
    ig_access_token: Optional[str] = None


@api.get("/settings")
async def read_settings(user=Depends(current_user)):
    s = await get_settings()
    tok = s.pop("ig_access_token", "")
    s["ig_token_set"] = bool(tok)
    s["ig_token_preview"] = f"{tok[:6]}…{tok[-4:]}" if tok else ""
    return s


@api.put("/settings")
async def update_settings(body: SettingsIn, user=Depends(current_user)):
    data = body.model_dump()
    if data["default_template"] not in TEMPLATES:
        raise HTTPException(422, "Unknown template")
    if not data.get("ig_access_token"):
        data.pop("ig_access_token")
    await db.settings.update_one({"key": "main"}, {"$set": data}, upsert=True)
    return await read_settings(user)


# ---------- AI ----------
SYSTEM_PROMPT = """You are the senior editor of an Instagram news channel. From raw notes you write sharp, factual carousel posts.
Rules: never mention any social media @handles; never invent or speculate on facts not present in the notes (no "still being assessed" style filler); neutral, punchy news tone; write in English.
Return ONLY valid JSON (no markdown) with this exact shape:
{"kicker": "1-2 word label e.g. BREAKING, POLITICS, WORLD, SPORTS, BUSINESS",
 "headline": "cover headline, max 12 words, strong and clear",
 "slides": [{"title": "max 6 words", "body": "1-3 short factual sentences, max 45 words"}],
 "caption": "Instagram caption, 2-4 short paragraphs summarising the story, ends with a call to follow for updates",
 "hashtags": ["#tag1", "#tag2"]}
slides: 2 to 4 items covering key facts (what, where, who, why/what next). hashtags: 8 to 15 relevant tags."""


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("AI returned no JSON")
    return json.loads(m.group(0))


async def ai_generate(raw_text: str, kicker_hint: str = ""):
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=str(uuid.uuid4()), system_message=SYSTEM_PROMPT).with_model("gemini", "gemini-3-flash-preview")
    prompt = f"Raw news notes:\n{raw_text}"
    if kicker_hint:
        prompt += f"\n\nPreferred label/category: {kicker_hint}"
    out = await chat.send_message(UserMessage(text=prompt))
    data = parse_json(out)
    tags = [t if t.startswith("#") else f"#{t}" for t in data.get("hashtags", [])]
    return {
        "kicker": (data.get("kicker") or kicker_hint or "NEWS")[:24],
        "headline": data["headline"],
        "slides": [{"title": s["title"], "body": s["body"]} for s in data.get("slides", [])][:6],
        "caption": data.get("caption", ""),
        "hashtags": " ".join(tags),
    }


# ---------- render ----------
async def render_post(post: dict):
    s = await get_settings()
    tpl = TEMPLATES.get(post.get("template"), TEMPLATES["bw_informative"])
    photos = [await run_in_threadpool(get_object, p) for p in post["source_images"]]
    date_str = datetime.now(timezone.utc).strftime("%d %b %Y").upper()
    total = 1 + len(post["slides"])
    credit = post.get("photo_credit", "")
    adjs = post.get("photo_adjust") or []
    adj = lambda k: adjs[k] if k < len(adjs) else None
    out = [await run_in_threadpool(tpl["cover"], photos[0], post["headline"], post["kicker"], s["brand_name"], date_str, credit, adj(0))]
    for i, sl in enumerate(post["slides"]):
        ph = photos[(i + 1) % len(photos)]
        out.append(await run_in_threadpool(tpl["detail"], ph, sl["title"], sl["body"], s["brand_name"], i + 2, total, credit, adj(i + 1)))
    return [await save_file(b, "jpg", "image/jpeg", "rendered") for b in out]


def full_caption(post, settings):
    tags = post.get("hashtags", "").strip()
    default = settings.get("default_hashtags", "").strip()
    merged = " ".join(dict.fromkeys((tags + " " + default).split()))
    return f"{post.get('caption', '').strip()}\n\n{merged}".strip()[:2200]


def present(post):
    post["rendered_urls"] = [media_url(p) for p in post.get("rendered_images", [])]
    post["source_urls"] = [media_url(p) for p in post.get("source_images", [])]
    return post


# ---------- posts ----------
@api.post("/posts")
async def create_post(raw_text: str = Form(...), kicker: str = Form(""), template: str = Form(""), photo_credit: Optional[str] = Form(None), images: List[UploadFile] = File(...), user=Depends(current_user)):
    if not raw_text.strip():
        raise HTTPException(422, "Raw text is required")
    settings = await get_settings()
    template = template or settings["default_template"]
    if template not in TEMPLATES:
        raise HTTPException(422, "Unknown template")
    if photo_credit is None:
        photo_credit = settings["default_photo_credit"]
    if not images or len(images) > 10:
        raise HTTPException(422, "Upload 1 to 10 images")
    paths = []
    for f in images:
        if not (f.content_type or "").startswith("image/"):
            raise HTTPException(422, f"{f.filename} is not an image")
        ext = (f.filename.rsplit(".", 1)[-1] if "." in f.filename else "jpg").lower()
        paths.append(await save_file(await f.read(), ext, f.content_type, "uploads"))
    try:
        gen = await ai_generate(raw_text, kicker.strip())
    except Exception as e:
        logger.exception("AI generation failed")
        raise HTTPException(502, f"AI generation failed: {e}")
    post = {"id": str(uuid.uuid4()), "raw_text": raw_text, "source_images": paths, "template": template, "photo_credit": photo_credit.strip(), "photo_adjust": [], **gen, "status": "pending_review", "created_at": now_iso(), "updated_at": now_iso()}
    post["rendered_images"] = await render_post(post)
    await db.posts.insert_one(dict(post))
    return present(post)


@api.get("/posts")
async def list_posts(status: Optional[str] = None, user=Depends(current_user)):
    q = {"status": status} if status else {}
    posts = await db.posts.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [present(p) for p in posts]


async def load_post(pid):
    post = await db.posts.find_one({"id": pid}, {"_id": 0})
    if not post:
        raise HTTPException(404, "Post not found")
    return post


@api.get("/posts/{pid}")
async def get_post(pid: str, user=Depends(current_user)):
    return present(await load_post(pid))


class SlideIn(BaseModel):
    title: str
    body: str


class PhotoAdjust(BaseModel):
    x: float = 0.5
    y: float = 0.4
    zoom: float = 1.0


class PostEdit(BaseModel):
    template: str = "bw_informative"
    photo_credit: str = ""
    photo_adjust: List[PhotoAdjust] = []
    kicker: str
    headline: str
    slides: List[SlideIn]
    caption: str
    hashtags: str


@api.put("/posts/{pid}")
async def edit_post(pid: str, body: PostEdit, user=Depends(current_user)):
    post = await load_post(pid)
    if post["status"] == "published":
        raise HTTPException(400, "Already published")
    upd = body.model_dump()
    if upd["template"] not in TEMPLATES:
        raise HTTPException(422, "Unknown template")
    post.update(upd)
    upd["rendered_images"] = await render_post(post)
    upd.update({"updated_at": now_iso(), "status": "pending_review"})
    await db.posts.update_one({"id": pid}, {"$set": upd})
    return present(await load_post(pid))


@api.post("/posts/{pid}/regenerate")
async def regenerate(pid: str, user=Depends(current_user)):
    post = await load_post(pid)
    if post["status"] == "published":
        raise HTTPException(400, "Already published")
    try:
        gen = await ai_generate(post["raw_text"])
    except Exception as e:
        raise HTTPException(502, f"AI generation failed: {e}")
    post.update(gen)
    gen["rendered_images"] = await render_post(post)
    gen.update({"updated_at": now_iso(), "status": "pending_review"})
    await db.posts.update_one({"id": pid}, {"$set": gen})
    return present(await load_post(pid))


@api.post("/posts/{pid}/reject")
async def reject(pid: str, user=Depends(current_user)):
    await load_post(pid)
    await db.posts.update_one({"id": pid}, {"$set": {"status": "rejected", "updated_at": now_iso()}})
    return present(await load_post(pid))


@api.delete("/posts/{pid}")
async def delete_post(pid: str, user=Depends(current_user)):
    await db.posts.delete_one({"id": pid})
    return {"ok": True}


# ---------- instagram ----------
async def meta(client_, method, path, data):
    r = await client_.request(method, f"{GRAPH}/{path}", **({"params": data} if method == "GET" else {"data": data}))
    js = r.json()
    if r.is_error or "error" in js:
        raise HTTPException(502, f"Instagram error: {js.get('error', {}).get('message', r.text)}")
    return js


async def wait_ready(c, cid, token):
    for _ in range(40):
        st = await meta(c, "GET", cid, {"fields": "status_code", "access_token": token})
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise HTTPException(502, f"Instagram media processing failed ({st.get('status_code')})")
        await asyncio.sleep(3)
    raise HTTPException(504, "Instagram media processing timed out")


async def publish_to_instagram(urls, caption, ig_id, token):
    async with httpx.AsyncClient(timeout=60) as c:
        if len(urls) == 1:
            cid = (await meta(c, "POST", f"{ig_id}/media", {"image_url": urls[0], "caption": caption, "access_token": token}))["id"]
        else:
            children = []
            for u in urls:
                children.append((await meta(c, "POST", f"{ig_id}/media", {"image_url": u, "is_carousel_item": "true", "access_token": token}))["id"])
            for ch in children:
                await wait_ready(c, ch, token)
            cid = (await meta(c, "POST", f"{ig_id}/media", {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption, "access_token": token}))["id"]
        await wait_ready(c, cid, token)
        pub = await meta(c, "POST", f"{ig_id}/media_publish", {"creation_id": cid, "access_token": token})
        link = await meta(c, "GET", pub["id"], {"fields": "permalink", "access_token": token})
        return pub["id"], link.get("permalink")


@api.post("/posts/{pid}/approve")
async def approve(pid: str, request: Request, user=Depends(current_user)):
    post = await load_post(pid)
    if post["status"] == "published":
        raise HTTPException(400, "Already published")
    s = await get_settings()
    if not s["ig_user_id"] or not s["ig_access_token"]:
        raise HTTPException(400, "Connect Instagram in Settings first (IG User ID + access token)")
    await db.posts.update_one({"id": pid}, {"$set": {"status": "publishing", "approved_at": now_iso()}})
    try:
        media_id, permalink = await publish_to_instagram([media_url(p, public_base(request)) for p in post["rendered_images"]], full_caption(post, s), s["ig_user_id"], s["ig_access_token"])
    except HTTPException as e:
        await db.posts.update_one({"id": pid}, {"$set": {"status": "failed", "error": e.detail}})
        raise
    except Exception as e:
        await db.posts.update_one({"id": pid}, {"$set": {"status": "failed", "error": str(e)}})
        raise HTTPException(502, f"Publishing failed: {e}")
    await db.posts.update_one({"id": pid}, {"$set": {"status": "published", "instagram_media_id": media_id, "permalink": permalink, "published_at": now_iso(), "error": None}})
    return present(await load_post(pid))


# ---------- public media (Instagram must fetch these) ----------
@api.get("/media/{path:path}")
async def media(path: str):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not rec:
        raise HTTPException(404, "File not found")
    data = await run_in_threadpool(get_object, path)
    return Response(content=data, media_type=rec["content_type"], headers={"Cache-Control": "public, max-age=31536000"})


@api.get("/templates")
async def templates():
    return [{"id": k, "name": v["name"]} for k, v in TEMPLATES.items()]


@api.get("/")
async def root():
    return {"message": "News Desk API"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.environ["FRONTEND_URL"].split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.files.create_index("storage_path")
    await db.posts.create_index("id", unique=True)
    email = os.environ["ADMIN_EMAIL"].lower()
    pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": email, "password_hash": hash_pw(pw), "name": "Admin", "role": "admin", "created_at": now_iso()})
    elif not verify_pw(pw, existing["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_pw(pw)}})
    try:
        init_storage()
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
