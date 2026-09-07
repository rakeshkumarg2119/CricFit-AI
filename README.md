# CricFit AI - temporary test backend

This is a throwaway backend, only for you to test the batting, bowling, and
Yo-Yo pipelines yourself while your teammate's real backend isn't ready yet.
Once the real backend exists, this folder can be deleted or handed over as a
reference for how the three modules wire together.

## Folder layout expected

```
CricFit AI/
├── batting_model/          (as-is from Colab export)
├── bowling_model/          (as-is from Colab export)
├── yoyo_test_model/        (the module Claude built earlier)
└── temp_test_backend/      (this folder)
```

All four folders must be siblings, at the same level, for the imports in
`main.py` to resolve.

## Setup

```bash
cd temp_test_backend
pip install -r requirements.txt
cp .env.example .env        # then paste your real GROQ_API_KEY in when you have one
uvicorn main:app --reload --port 8000
```

First startup will be slow - it loads 5 Keras models (batting classifier,
bowling action-filter/arm/pace classifiers) plus 3 MediaPipe pose models.

**ffmpeg is also required** (for the annotated-video output below) - it must
be installed and on your system PATH. Without it, `/analyze` endpoints still
return the JSON report/tips fine, just with `annotated_video_url: null`.

## Endpoints to test with Postman / your frontend

| Endpoint | Method | Body | Notes |
|---|---|---|---|
| `/health` | GET | - | Confirms server is up |
| `/api/batting/analyze` | POST | form-data: `video` | Shot classification + Stage 2 report |
| `/api/bowling/analyze` | POST | form-data: `video` | Action classification + closest-pro-match |
| `/api/yoyo/analyze` | POST | form-data: `video`, `yoyo_level` (required, e.g. `"16.3"`), `target_score` (optional), `target_board` (optional) | Cadence + protocol-compliance report |
| `/api/tips` | POST | json: `{"report": {...}, "sport": "batting"}` | Sends any report JSON to Groq for tips text |

Every `/analyze` call automatically sends its report to Groq and returns the
tips inline under a `"tips"` key in the same response - no extra flag needed.

## Annotated (skeleton-overlay) video

Every `/analyze` call also renders a video with the MediaPipe pose overlay
plus a side report panel, saved on disk under
`temp_test_backend/analyzed_videos/<sport>/<random-id>.mp4`, and served back
statically. The response includes:

```json
"annotated_video_url": "http://127.0.0.1:8000/analyzed_videos/batting/ab12cd34.mp4"
```

Paste that URL into a browser tab (or Postman's response Preview) to watch
it directly. Batting and bowling reuse their own existing
`generate_annotated_report_video()`/`generate_annotated_video()` functions.
The yoyo module didn't have an annotated-video function before, so a new
file was added - `yoyo_test_model/annotated_video.py` - that draws the
skeleton + a shuttle-count/cadence-trend panel; it doesn't touch
`tracker.py` or `video_pipeline.py`.

If `annotated_video_url` comes back `null`, check `annotated_video_note` in
the same response - it'll say whether ffmpeg is missing or rendering failed,
without blocking the JSON report/tips you already got.

## Groq testing

You said you don't have the key yet - the wiring (`groq_client.py`) is done
and ready. Until `GROQ_API_KEY` is set in `.env`, the `"tips"` field on
every response will be:

```json
{"error": "GROQ_API_KEY is not set. Add it to your .env file (copy .env.example) and restart the server."}
```

so you'll see clearly whether it's a missing-key issue or an actual API
error once you drop your real key in. It never crashes the batting/bowling/
yoyo endpoints themselves - the rest of the report still comes back fine,
just with that `error` field inside `"tips"` until the key is in place.

## Known constraints

- Heavy install: `tensorflow` + `mediapipe` are large - first `pip install`
  will take a while.
- `bowling_model`'s config hardcodes its own `models/`/`data/` paths
  relative to its own folder - `main.py` already handles this by switching
  directory briefly on import, so you don't need to touch it.
- This backend has no database, no auth, and no real error-recovery. It is
  for local testing only.
