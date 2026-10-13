# PRD — Instagram NewsDesk

## Original problem
Instagram news channel: upload raw news photo(s) + draft raw text; AI generates a well-designed news-portal-style Instagram carousel (headline on images, caption + hashtags); auto-publish to Instagram after manual approval. Low credit usage.

## User choices
Gemini 3 Flash (Emergent key) · Template-based Pillow overlay (no AI images) · Instagram Graph API (token + IG User ID entered in Settings) · Single admin JWT login · Black & white branding.

## Architecture
- FastAPI (server.py, render.py) + MongoDB (users, settings, posts, files) + Emergent Object Storage
- render.py: 1080x1350 JPEG cover (photo + gradient + headline) and detail slides (photo top, text below), fonts in backend/fonts
- Public /api/media/{path} serves images (Instagram fetches these); publish uses request host as base URL
- React pages: Login, Desk (dashboard), New Story, Review (IG preview + edit + approve), Settings

## Implemented (2026-06)
- Admin auth (cookies), settings with masked token
- Upload → 1 AI call → render → review → edit/re-render (no AI) → rewrite with AI → approve & publish (single/carousel) → status/permalink
- Tested: 17/17 backend tests, frontend flows pass. Real IG publish untested (no real token).

## Iteration 2 (2026-06)
- Templates: 'Black And White Informative' (4:5) and 'Standard' (1:1, ANI-style photo + dark panel, red line, centered headline, red chevrons)
- Channel name ANI, no @handles, ANI logo top-right on every slide; template picker on New Story + switch on Review (re-render, no AI)

## Backlog
- P1: Hindi/regional language fonts; multiple template styles; token expiry reminder
- P2: Scheduled publishing; post analytics
