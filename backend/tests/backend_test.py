"""Backend regression tests for News Desk portal - iteration 2.

Focus: multi-template support (bw_informative 1080x1350, standard 1080x1080),
no 'handle' field in settings, brand_name default ANI.
Budget: at most 1 POST /api/posts call (one AI generation).
"""
import io
import os
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://news-carousel-3.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@newsdesk.com"
ADMIN_PASSWORD = "NewsDesk@2026"

RAW_TEXT = (
    "A magnitude 6.1 earthquake struck off the coast of northern Japan early Tuesday morning. "
    "Authorities issued a brief tsunami advisory which was later lifted. "
    "No casualties have been reported so far. Power outages affected about 2,000 homes in Hokkaido."
)


def _img_bytes(color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (1600, 1200), color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


# ---------- quick auth smoke ----------
def test_auth_me(client):
    r = client.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


# ---------- templates ----------
def test_templates_endpoint(client):
    r = client.get(f"{BASE_URL}/api/templates")
    assert r.status_code == 200
    tpls = r.json()
    assert isinstance(tpls, list) and len(tpls) == 2
    by_id = {t["id"]: t for t in tpls}
    assert "bw_informative" in by_id
    assert "standard" in by_id
    assert by_id["bw_informative"]["name"] == "Black And White Informative"
    assert by_id["standard"]["name"] == "Standard"


# ---------- settings (no 'handle' field) ----------
def test_settings_no_handle_default_ani(client):
    r = client.get(f"{BASE_URL}/api/settings")
    assert r.status_code == 200
    d = r.json()
    assert "brand_name" in d
    assert "handle" not in d, f"'handle' should be removed from settings, got: {d}"
    # Ensure default brand_name is ANI if nothing persisted overrides it.
    # (Previous iteration test may have saved 'News Desk'; reset to ANI to validate)
    reset = client.put(f"{BASE_URL}/api/settings", json={
        "brand_name": "ANI",
        "default_hashtags": "#ANI #news #breakingnews",
        "ig_user_id": "",
    })
    assert reset.status_code == 200
    assert reset.json()["brand_name"] == "ANI"
    assert "handle" not in reset.json()


def test_settings_update_rejects_handle_silently(client):
    # Pydantic model excludes 'handle' — extra field is ignored (default behaviour).
    r = client.put(f"{BASE_URL}/api/settings", json={
        "brand_name": "ANI",
        "handle": "@shouldbeignored",
        "default_hashtags": "#ANI",
        "ig_user_id": "",
    })
    assert r.status_code == 200
    assert "handle" not in r.json()


# ---------- post create with 'standard' template (ONE AI call budget) ----------
@pytest.fixture(scope="session")
def standard_post(client):
    files = [
        ("images", ("a.jpg", _img_bytes("red"), "image/jpeg")),
        ("images", ("b.jpg", _img_bytes("navy"), "image/jpeg")),
    ]
    data = {"raw_text": RAW_TEXT, "kicker": "WORLD", "template": "standard"}
    r = client.post(f"{BASE_URL}/api/posts", data=data, files=files, timeout=180)
    assert r.status_code == 200, f"Create post failed: {r.status_code} {r.text}"
    p = r.json()
    assert p["template"] == "standard"
    return p


def _fetch_image(url):
    if url.startswith("/"):
        url = BASE_URL + url
    r = requests.get(url, timeout=90)
    assert r.status_code == 200, f"Failed to fetch {url}: {r.status_code}"
    assert r.headers["content-type"].startswith("image/jpeg")
    return Image.open(io.BytesIO(r.content))


def test_standard_renders_1080x1080(standard_post):
    assert len(standard_post["rendered_urls"]) == 1 + len(standard_post["slides"])
    for u in standard_post["rendered_urls"]:
        im = _fetch_image(u)
        assert im.size == (1080, 1080), f"Expected 1080x1080 for standard, got {im.size} for {u}"


def test_switch_to_bw_informative_rerenders_1080x1350(client, standard_post):
    pid = standard_post["id"]
    before_urls = standard_post["rendered_urls"]
    edit = {
        "template": "bw_informative",
        "kicker": standard_post["kicker"],
        "headline": standard_post["headline"],
        "slides": standard_post["slides"],
        "caption": standard_post["caption"],
        "hashtags": standard_post["hashtags"],
    }
    r = client.put(f"{BASE_URL}/api/posts/{pid}", json=edit, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["template"] == "bw_informative"
    assert d["rendered_urls"] != before_urls, "Expected re-render with new URLs"
    for u in d["rendered_urls"]:
        im = _fetch_image(u)
        assert im.size == (1080, 1350), f"Expected 1080x1350 for bw_informative, got {im.size}"


def test_switch_back_to_standard_rerenders_1080x1080(client, standard_post):
    pid = standard_post["id"]
    # Fetch current state
    cur = client.get(f"{BASE_URL}/api/posts/{pid}").json()
    edit = {
        "template": "standard",
        "kicker": cur["kicker"],
        "headline": cur["headline"],
        "slides": cur["slides"],
        "caption": cur["caption"],
        "hashtags": cur["hashtags"],
    }
    r = client.put(f"{BASE_URL}/api/posts/{pid}", json=edit, timeout=120)
    assert r.status_code == 200
    for u in r.json()["rendered_urls"]:
        im = _fetch_image(u)
        assert im.size == (1080, 1080)


def test_invalid_template_on_create(client):
    files = [("images", ("a.jpg", _img_bytes(), "image/jpeg"))]
    r = client.post(f"{BASE_URL}/api/posts", data={"raw_text": RAW_TEXT, "template": "bogus"}, files=files)
    assert r.status_code == 422, f"Expected 422 got {r.status_code}: {r.text}"


def test_invalid_template_on_edit(client, standard_post):
    pid = standard_post["id"]
    edit = {
        "template": "bogus",
        "kicker": "X", "headline": "x", "slides": [{"title": "a", "body": "b"}],
        "caption": "c", "hashtags": "#x",
    }
    r = client.put(f"{BASE_URL}/api/posts/{pid}", json=edit)
    assert r.status_code == 422


# ---------- cleanup ----------
def test_zz_cleanup(client, standard_post):
    pid = standard_post["id"]
    client.delete(f"{BASE_URL}/api/posts/{pid}")
    assert client.get(f"{BASE_URL}/api/posts/{pid}").status_code == 404
