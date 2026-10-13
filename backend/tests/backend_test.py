"""Backend regression tests for News Desk portal."""
import io
import os
import time
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
    Image.new("RGB", (1200, 800), color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


# ---------- auth ----------
class TestAuth:
    def test_root(self):
        r = requests.get(f"{BASE_URL}/api/")
        assert r.status_code == 200

    def test_login_wrong_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401
        assert "Invalid" in r.json().get("detail", "")

    def test_login_me_logout(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL
        assert "access_token" in s.cookies
        me = s.get(f"{BASE_URL}/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == ADMIN_EMAIL
        assert "password_hash" not in me.json()
        lo = s.post(f"{BASE_URL}/api/auth/logout")
        assert lo.status_code == 200

    def test_me_unauth(self):
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401


# ---------- settings ----------
class TestSettings:
    def test_get(self, client):
        r = client.get(f"{BASE_URL}/api/settings")
        assert r.status_code == 200
        d = r.json()
        assert "brand_name" in d and "handle" in d
        assert "ig_token_set" in d and "ig_token_preview" in d
        assert "ig_access_token" not in d

    def test_update_and_token_mask(self, client):
        # set
        payload = {
            "brand_name": "News Desk",
            "handle": "@newsdesk",
            "default_hashtags": "#news #breaking",
            "ig_user_id": "1234567890",
            "ig_access_token": "EAABtest_token_XYZ1234",
        }
        r = client.put(f"{BASE_URL}/api/settings", json=payload)
        assert r.status_code == 200
        d = r.json()
        assert d["brand_name"] == "News Desk"
        assert d["ig_user_id"] == "1234567890"
        assert d["ig_token_set"] is True
        assert "…" in d["ig_token_preview"]

        # Blank token keeps existing
        payload2 = {**payload, "ig_access_token": ""}
        r2 = client.put(f"{BASE_URL}/api/settings", json=payload2)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["ig_token_set"] is True, "Blank token should keep existing"
        assert d2["ig_token_preview"] == d["ig_token_preview"]


# ---------- posts ----------
@pytest.fixture(scope="class")
def created_post(client):
    files = [
        ("images", ("a.jpg", _img_bytes("red"), "image/jpeg")),
        ("images", ("b.jpg", _img_bytes("blue"), "image/jpeg")),
    ]
    data = {"raw_text": RAW_TEXT, "kicker": "BREAKING"}
    r = client.post(f"{BASE_URL}/api/posts", data=data, files=files, timeout=120)
    assert r.status_code == 200, f"Create post failed: {r.status_code} {r.text}"
    return r.json()


class TestPosts:
    def test_create_post(self, created_post):
        p = created_post
        assert p["status"] == "pending_review"
        assert p["headline"]
        assert 2 <= len(p["slides"]) <= 6
        assert len(p["rendered_urls"]) == 1 + len(p["slides"])
        for u in p["rendered_urls"]:
            assert u.startswith("http")

    def test_rendered_url_public(self, created_post):
        u = created_post["rendered_urls"][0]
        r = requests.get(u, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/jpeg")
        assert len(r.content) > 1000

    def test_list_posts(self, client):
        r = client.get(f"{BASE_URL}/api/posts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_posts(self, client):
        r = client.get(f"{BASE_URL}/api/posts", params={"status": "pending_review"})
        assert r.status_code == 200
        for p in r.json():
            assert p["status"] == "pending_review"

    def test_edit_post_rerenders(self, client, created_post):
        pid = created_post["id"]
        before = created_post["rendered_urls"]
        edit = {
            "kicker": "WORLD",
            "headline": "Edited Headline For Rerender Test Case",
            "slides": [{"title": "New Title", "body": "New body text here."}, {"title": "Second", "body": "Another body."}],
            "caption": "Edited caption text.",
            "hashtags": "#edited #news",
        }
        r = client.put(f"{BASE_URL}/api/posts/{pid}", json=edit)
        assert r.status_code == 200
        d = r.json()
        assert d["headline"] == edit["headline"]
        assert d["kicker"] == "WORLD"
        assert len(d["slides"]) == 2
        assert len(d["rendered_urls"]) == 3
        assert d["rendered_urls"] != before  # re-rendered

    def test_approve_without_ig_creds(self, client, created_post):
        # Clear IG creds
        client.put(f"{BASE_URL}/api/settings", json={
            "brand_name": "News Desk", "handle": "@newsdesk",
            "default_hashtags": "#news", "ig_user_id": "", "ig_access_token": "",
        })
        # Need to also wipe existing token (blank keeps). Use direct dummy approach:
        # Since blank preserves token, we have to set a value then rely on empty ig_user_id blocking.
        # Code checks: if not ig_user_id or not ig_access_token -> 400
        pid = created_post["id"]
        r = client.post(f"{BASE_URL}/api/posts/{pid}/approve")
        assert r.status_code == 400
        assert "Connect Instagram" in r.json()["detail"]

    def test_approve_with_fake_creds_fails(self, client, created_post):
        client.put(f"{BASE_URL}/api/settings", json={
            "brand_name": "News Desk", "handle": "@newsdesk",
            "default_hashtags": "#news", "ig_user_id": "17841400000000000",
            "ig_access_token": "FAKE_TOKEN_FOR_TESTING_ONLY_XYZ",
        })
        pid = created_post["id"]
        r = client.post(f"{BASE_URL}/api/posts/{pid}/approve", timeout=60)
        assert r.status_code == 502
        # Verify status now failed
        g = client.get(f"{BASE_URL}/api/posts/{pid}")
        assert g.status_code == 200
        assert g.json()["status"] == "failed"
        assert g.json().get("error")

    def test_reject(self, client, created_post):
        pid = created_post["id"]
        r = client.post(f"{BASE_URL}/api/posts/{pid}/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_delete(self, client, created_post):
        pid = created_post["id"]
        r = client.delete(f"{BASE_URL}/api/posts/{pid}")
        assert r.status_code == 200
        g = client.get(f"{BASE_URL}/api/posts/{pid}")
        assert g.status_code == 404


class TestValidation:
    def test_create_requires_images(self, client):
        r = client.post(f"{BASE_URL}/api/posts", data={"raw_text": "hi", "kicker": ""})
        assert r.status_code in (422, 400)

    def test_create_empty_text(self, client):
        files = [("images", ("a.jpg", _img_bytes(), "image/jpeg"))]
        r = client.post(f"{BASE_URL}/api/posts", data={"raw_text": "   ", "kicker": ""}, files=files)
        assert r.status_code == 422
