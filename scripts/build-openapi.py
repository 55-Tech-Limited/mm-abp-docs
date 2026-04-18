#!/usr/bin/env python3
"""
Filter the MM API OpenAPI spec to the 23 published operations and write the
result to both `mm-api/openapi.json` and `zh/mm-api/openapi.json`.

Source of truth: `mm-api/openapi-internal.json` (full unfiltered spec exported
from the backend). On the first run this file is bootstrapped from the current
`mm-api/openapi.json`. To pull in new backend endpoints, replace
`openapi-internal.json` with a fresh export and rerun this script.

Usage: python scripts/build-openapi.py
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTERNAL = REPO / "mm-api" / "openapi-internal.json"
EN_OUT = REPO / "mm-api" / "openapi.json"
ZH_OUT = REPO / "zh" / "mm-api" / "openapi.json"

# (path, method) -> short summary + description override.
# Replaces verbose FastAPI-generated text with a single-line summary and a
# one-sentence description. Long-form details belong in the prose pages
# (overview, quickstart, websocket).
OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    # Trading Controls
    ("/api/v1/trading/status", "get"): (
        "Trading status",
        "Current engine state for your client.",
    ),
    ("/api/v1/trading/pause", "post"): (
        "Pause trading",
        "Stop posting new orders. Existing resting orders stay live.",
    ),
    ("/api/v1/trading/resume", "post"): (
        "Resume trading",
        "Resume after a manual pause.",
    ),
    ("/api/v1/trading/stop", "post"): (
        "Stop trading",
        "Stop the engine and cancel all open orders.",
    ),
    ("/api/v1/trading/start", "post"): (
        "Start trading",
        "Start the engine after a stop.",
    ),
    # Orders & Bets
    ("/api/v1/orders", "get"): (
        "List orders",
        "Paginated list of exchange orders. Filter by fixture, status, exchange, or date.",
    ),
    ("/api/v1/orders/open", "get"): (
        "List open orders",
        "All currently resting or partially-filled orders.",
    ),
    ("/api/v1/orders/summary", "get"): (
        "Orders summary",
        "Aggregated order statistics.",
    ),
    ("/api/v1/orders/cancel-all", "post"): (
        "Cancel all orders",
        "Cancel every open order across all exchanges.",
    ),
    ("/api/v1/orders/{order_id}/cancel", "post"): (
        "Cancel order",
        "Cancel a single order by ID.",
    ),
    ("/api/v1/bets", "get"): (
        "List hedge bets",
        "Paginated list of bets placed on bookmakers to hedge filled orders.",
    ),
    ("/api/v1/bets/summary", "get"): (
        "Bets summary",
        "Aggregated hedge bet statistics.",
    ),
    # Performance
    ("/api/v1/positions", "get"): (
        "List positions",
        "Hedged positions grouped by fixture.",
    ),
    ("/api/v1/positions/summary", "get"): (
        "Positions summary",
        "Aggregated position statistics.",
    ),
    ("/api/v1/pnl", "get"): (
        "P&L",
        "Profit & loss and turnover for your client.",
    ),
    ("/api/v1/accounts", "get"): (
        "List accounts",
        "Exchange account balances and status. Credentials are never returned.",
    ),
    # Configuration
    ("/api/v1/sports/{sport_id}/market-types", "get"): (
        "List market types",
        "Tradeable market types for a sport with your per-client toggle status.",
    ),
    ("/api/v1/client/market-allowlist", "patch"): (
        "Toggle market types",
        "Enable or disable market types in bulk.",
    ),
    ("/api/v1/client/market-allowlist/activate-all", "post"): (
        "Re-enable all market types",
        "Reset all market type toggles to enabled.",
    ),
    ("/api/v1/tournaments", "get"): (
        "List tournaments",
        "Your tournaments with activation status.",
    ),
    ("/api/v1/tournaments/{tournament_id}/activate", "post"): (
        "Activate tournament",
        "Start trading a tournament.",
    ),
    ("/api/v1/tournaments/{tournament_id}/deactivate", "post"): (
        "Deactivate tournament",
        "Stop trading a tournament. Cancels its open orders.",
    ),
}

# (path, method) -> sidebar tag
PUBLISHED: dict[tuple[str, str], str] = {
    # Trading Controls (5)
    ("/api/v1/trading/status", "get"): "Trading Controls",
    ("/api/v1/trading/pause", "post"): "Trading Controls",
    ("/api/v1/trading/resume", "post"): "Trading Controls",
    ("/api/v1/trading/stop", "post"): "Trading Controls",
    ("/api/v1/trading/start", "post"): "Trading Controls",
    # Orders & Bets (7)
    ("/api/v1/orders", "get"): "Orders & Bets",
    ("/api/v1/orders/open", "get"): "Orders & Bets",
    ("/api/v1/orders/summary", "get"): "Orders & Bets",
    ("/api/v1/orders/cancel-all", "post"): "Orders & Bets",
    ("/api/v1/orders/{order_id}/cancel", "post"): "Orders & Bets",
    ("/api/v1/bets", "get"): "Orders & Bets",
    ("/api/v1/bets/summary", "get"): "Orders & Bets",
    # Performance (4)
    ("/api/v1/positions", "get"): "Performance",
    ("/api/v1/positions/summary", "get"): "Performance",
    ("/api/v1/pnl", "get"): "Performance",
    ("/api/v1/accounts", "get"): "Performance",
    # Configuration (6)
    ("/api/v1/sports/{sport_id}/market-types", "get"): "Configuration",
    ("/api/v1/client/market-allowlist", "patch"): "Configuration",
    ("/api/v1/client/market-allowlist/activate-all", "post"): "Configuration",
    ("/api/v1/tournaments", "get"): "Configuration",
    ("/api/v1/tournaments/{tournament_id}/activate", "post"): "Configuration",
    ("/api/v1/tournaments/{tournament_id}/deactivate", "post"): "Configuration",
}

TAG_DEFINITIONS = [
    {
        "name": "Trading Controls",
        "description": "Pause, resume, stop, and start your trading engine.",
    },
    {
        "name": "Orders & Bets",
        "description": "Inspect and cancel exchange orders, view hedge bets placed on bookmakers.",
    },
    {
        "name": "Performance",
        "description": "Hedged positions, P&L and turnover, exchange account balances.",
    },
    {
        "name": "Configuration",
        "description": "Choose which market types and tournaments your engine trades.",
    },
]

INFO_DESCRIPTION = """
## MM API

The MM engine places orders, hedges positions, and tracks P&L automatically.
This API lets you monitor trading activity, control your engine, and configure
which market types and tournaments to trade.

### Authentication
All endpoints require the `X-API-Key` header with your client UUID.

### Rate limits
- REST API: 2,000 requests/minute per client
- WebSocket: 5 concurrent connections per API key
"""

GENERATED_NOTE = (
    "GENERATED — do not hand-edit. "
    "Run `python scripts/build-openapi.py` to regenerate from "
    "`mm-api/openapi-internal.json`."
)

# Method-like keys that may appear inside a path item.
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def collect_referenced_schemas(root: dict, paths: dict) -> set[str]:
    """Walk paths transitively, collecting every schema name reached via $ref."""
    schemas = (root.get("components") or {}).get("schemas") or {}
    referenced: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if (
                    key == "$ref"
                    and isinstance(value, str)
                    and value.startswith("#/components/schemas/")
                ):
                    name = value.rsplit("/", 1)[-1]
                    if name not in referenced:
                        referenced.add(name)
                        if name in schemas:
                            visit(schemas[name])
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(paths)
    return referenced


def filter_spec(spec: dict) -> dict:
    new_paths: dict[str, dict] = {}
    seen: set[tuple[str, str]] = set()

    for path, item in (spec.get("paths") or {}).items():
        kept: dict[str, object] = {}
        for method, op in item.items():
            if method.lower() in HTTP_METHODS and (path, method.lower()) in PUBLISHED:
                tag = PUBLISHED[(path, method.lower())]
                op_copy = dict(op)
                op_copy["tags"] = [tag]
                override = OVERRIDES.get((path, method.lower()))
                if override:
                    summary, description = override
                    op_copy["summary"] = summary
                    op_copy["description"] = description
                kept[method.lower()] = op_copy
                seen.add((path, method.lower()))
        if kept:
            new_paths[path] = kept

    missing = sorted(set(PUBLISHED) - seen)
    if missing:
        sys.stderr.write(
            "WARNING: published operations not found in source spec:\n"
        )
        for path, method in missing:
            sys.stderr.write(f"  {method.upper()} {path}\n")

    referenced = collect_referenced_schemas(spec, new_paths)

    components = dict(spec.get("components") or {})
    schemas = components.get("schemas") or {}
    components["schemas"] = {
        name: schema for name, schema in schemas.items() if name in referenced
    }

    out: dict = {
        "openapi": spec.get("openapi", "3.1.0"),
        "info": dict(spec.get("info") or {}),
        "x-generated": GENERATED_NOTE,
        "tags": TAG_DEFINITIONS,
        "paths": new_paths,
        "components": components,
    }
    out["info"]["description"] = INFO_DESCRIPTION

    if "servers" in spec:
        out["servers"] = spec["servers"]
    if "security" in spec:
        out["security"] = spec["security"]

    return out


def main() -> int:
    if not INTERNAL.exists():
        if not EN_OUT.exists():
            sys.stderr.write(
                f"error: neither {INTERNAL} nor {EN_OUT} exists; "
                "drop a fresh backend export at openapi-internal.json first\n"
            )
            return 1
        INTERNAL.write_text(EN_OUT.read_text())
        print(f"bootstrapped {INTERNAL.relative_to(REPO)} from {EN_OUT.relative_to(REPO)}")

    spec = json.loads(INTERNAL.read_text())
    filtered = filter_spec(spec)
    payload = json.dumps(filtered, indent=2, ensure_ascii=False) + "\n"

    EN_OUT.write_text(payload)
    ZH_OUT.write_text(payload)

    op_count = sum(len(methods) for methods in filtered["paths"].values())
    schema_count = len((filtered.get("components") or {}).get("schemas") or {})
    print(
        f"wrote {op_count} operations, {schema_count} schemas to "
        f"{EN_OUT.relative_to(REPO)} and {ZH_OUT.relative_to(REPO)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
