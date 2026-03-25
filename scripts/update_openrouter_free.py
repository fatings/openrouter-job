import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

CURRENT = DATA / "current.json"
PREVIOUS = DATA / "previous.json"
DIFF = DATA / "diff.json"

API_URL = "https://openrouter.ai/api/v1/models"


def fetch_models():
    req = Request(API_URL, headers={"User-Agent": "github-actions-openrouter-check"})
    with urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode("utf-8"))
    return payload.get("data", payload)


def is_free(model):
    model_id = (model.get("id") or "").lower()
    return model_id.endswith(":free")


def normalize(model):
    return {
        "id": model.get("id"),
        "name": model.get("name"),
        "canonical_slug": model.get("canonical_slug"),
        "context_length": model.get("context_length"),
        "pricing": model.get("pricing"),
        "top_provider": model.get("top_provider"),
    }


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


all_models = fetch_models()
free_models = sorted(
    [normalize(m) for m in all_models if is_free(m)],
    key=lambda x: x["id"] or ""
)

previous = load_json(CURRENT, [])
previous_ids = {m["id"] for m in previous}
current_ids = {m["id"] for m in free_models}

added_ids = sorted(current_ids - previous_ids)
removed_ids = sorted(previous_ids - current_ids)

added = [m for m in free_models if m["id"] in added_ids]
removed = [m for m in previous if m["id"] in removed_ids]

if CURRENT.exists():
    PREVIOUS.write_text(CURRENT.read_text(encoding="utf-8"), encoding="utf-8")

CURRENT.write_text(
    json.dumps(free_models, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

diff_payload = {
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_current": len(free_models),
    "added_count": len(added),
    "removed_count": len(removed),
    "added": added,
    "removed": removed,
    "all_current_ids": sorted(current_ids),
}

DIFF.write_text(
    json.dumps(diff_payload, indent=2, ensure_ascii=False),
    encoding="utf-8"
)