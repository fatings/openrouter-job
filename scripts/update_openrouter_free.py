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

PRICING_FIELDS = [
    "prompt",
    "completion",
    "request",
    "image",
    "web_search",
    "internal_reasoning",
    "input_cache_read",
    "input_cache_write",
]

CORE_PRICING_FIELDS = ["prompt", "completion", "request"]


def fetch_models():
    req = Request(API_URL, headers={"User-Agent": "github-actions-openrouter-check"})
    with urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode("utf-8"))
    return payload.get("data", payload)


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyse_pricing(pricing):
    if not isinstance(pricing, dict):
        pricing = {}

    parsed = {}
    for key in PRICING_FIELDS:
        if key in pricing:
            num = to_float(pricing.get(key))
            if num is not None:
                parsed[key] = num

    has_pricing = len(parsed) > 0
    zero_fields = sorted([k for k, v in parsed.items() if v == 0])
    non_zero_fields = sorted([k for k, v in parsed.items() if v != 0])

    core_present = [k for k in CORE_PRICING_FIELDS if k in parsed]
    core_zero = len(core_present) > 0 and all(parsed[k] == 0 for k in core_present)
    all_zero = has_pricing and all(v == 0 for v in parsed.values())

    return {
        "has_pricing": has_pricing,
        "parsed": parsed,
        "zero_fields": zero_fields,
        "non_zero_fields": non_zero_fields,
        "core_present": core_present,
        "core_zero": core_zero,
        "all_zero": all_zero,
    }


def classify_free(model):
    model_id = (model.get("id") or "").lower()
    suffix_free = model_id.endswith(":free")
    pricing = analyse_pricing(model.get("pricing"))

    if suffix_free and pricing["all_zero"]:
        return True, "suffix_and_all_zero_pricing"

    if suffix_free and pricing["core_zero"]:
        return True, "suffix_and_core_zero_pricing"

    if not suffix_free and pricing["all_zero"]:
        return True, "all_zero_pricing_only"

    if not suffix_free and pricing["core_zero"]:
        return True, "core_zero_pricing_only"

    if suffix_free and pricing["non_zero_fields"]:
        return False, "suffix_but_nonzero_pricing:" + ",".join(pricing["non_zero_fields"])

    if suffix_free and not pricing["has_pricing"]:
        return False, "suffix_but_no_pricing"

    if not suffix_free and pricing["non_zero_fields"]:
        return False, "nonzero_pricing:" + ",".join(pricing["non_zero_fields"])

    return False, "no_free_suffix_and_no_zero_pricing"


def normalize(model):
    is_free, free_reason = classify_free(model)
    pricing_info = analyse_pricing(model.get("pricing"))

    return {
        "id": model.get("id"),
        "name": model.get("name"),
        "canonical_slug": model.get("canonical_slug"),
        "created": model.get("created"),
        "context_length": model.get("context_length"),
        "supported_parameters": model.get("supported_parameters"),
        "pricing": model.get("pricing"),
        "top_provider": model.get("top_provider"),
        "is_free": is_free,
        "free_reason": free_reason,
        "pricing_zero_fields": pricing_info["zero_fields"],
        "pricing_non_zero_fields": pricing_info["non_zero_fields"],
    }


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


all_models = fetch_models()
normalized_models = [normalize(m) for m in all_models]

free_models = sorted(
    [m for m in normalized_models if m["is_free"]],
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

reason_counts = {}
for model in free_models:
    reason = model.get("free_reason", "unknown")
    reason_counts[reason] = reason_counts.get(reason, 0) + 1

diff_payload = {
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "detection_policy": {
        "free_if": [
            "id endswith ':free' and all parsed pricing fields are zero",
            "id endswith ':free' and core pricing fields present are zero",
            "all parsed pricing fields are zero even without ':free'",
            "core pricing fields present are zero even without ':free'",
        ],
        "not_free_if": [
            "id endswith ':free' but any parsed pricing field is non-zero",
            "no ':free' suffix and parsed pricing is non-zero",
            "':free' suffix exists but pricing is missing",
        ],
    },
    "total_current": len(free_models),
    "added_count": len(added),
    "removed_count": len(removed),
    "free_reason_counts": reason_counts,
    "added": added,
    "removed": removed,
    "all_current_ids": sorted(current_ids),
}

DIFF.write_text(
    json.dumps(diff_payload, indent=2, ensure_ascii=False),
    encoding="utf-8"
            )
