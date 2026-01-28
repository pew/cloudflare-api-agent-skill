#!/usr/bin/env python3
"""
Cloudflare API Schema Tool - Fetch, cache, and query the OpenAPI schema.

Usage:
    cf_schema.py fetch              # Download/update schema (cached 24h)
    cf_schema.py search <query>     # Search endpoints by keyword
    cf_schema.py get <path>         # Get full spec for endpoint path
    cf_schema.py list [prefix]      # List all paths (optionally filtered)
    cf_schema.py info               # Show schema metadata and stats

Examples:
    cf_schema.py search dns         # Find DNS-related endpoints
    cf_schema.py search "zone"      # Find zone management endpoints
    cf_schema.py get "/zones"       # Get spec for /zones endpoint
    cf_schema.py list /accounts     # List all /accounts/* endpoints
"""

import json
import sys
import os
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

SCHEMA_URL = "https://raw.githubusercontent.com/cloudflare/api-schemas/refs/heads/main/openapi.json"
CACHE_DIR = Path.home() / ".cache" / "cloudflare-api"
CACHE_FILE = CACHE_DIR / "openapi.json"
CACHE_META = CACHE_DIR / "meta.json"
CACHE_HOURS = 24


def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def is_cache_valid() -> bool:
    """Check if cached schema exists and is fresh."""
    if not CACHE_FILE.exists() or not CACHE_META.exists():
        return False
    try:
        meta = json.loads(CACHE_META.read_text())
        cached_at = datetime.fromisoformat(meta["cached_at"])
        return datetime.now() - cached_at < timedelta(hours=CACHE_HOURS)
    except Exception:
        return False


def fetch_schema(force: bool = False) -> dict:
    """Fetch schema from GitHub, using cache if valid."""
    ensure_cache_dir()

    if not force and is_cache_valid():
        print(f"Using cached schema (< {CACHE_HOURS}h old)", file=sys.stderr)
        return json.loads(CACHE_FILE.read_text())

    print("Fetching latest Cloudflare API schema...", file=sys.stderr)
    try:
        with urllib.request.urlopen(SCHEMA_URL, timeout=60) as response:
            data = response.read().decode("utf-8")
            schema = json.loads(data)

        # Cache it
        CACHE_FILE.write_text(data)
        CACHE_META.write_text(
            json.dumps(
                {
                    "cached_at": datetime.now().isoformat(),
                    "version": schema.get("info", {}).get("version", "unknown"),
                    "paths_count": len(schema.get("paths", {})),
                }
            )
        )
        print(
            f"Cached schema: {len(schema.get('paths', {}))} endpoints", file=sys.stderr
        )
        return schema
    except Exception as e:
        print(f"Error fetching schema: {e}", file=sys.stderr)
        if CACHE_FILE.exists():
            print("Falling back to stale cache", file=sys.stderr)
            return json.loads(CACHE_FILE.read_text())
        raise


def load_schema() -> dict:
    """Load schema, fetching if needed."""
    if is_cache_valid():
        return json.loads(CACHE_FILE.read_text())
    return fetch_schema()


def search_endpoints(query: str, schema: dict) -> list:
    """Search endpoints by keyword in path, summary, or description."""
    results = []
    query_lower = query.lower()
    paths = schema.get("paths", {})

    for path, methods in paths.items():
        for method, spec in methods.items():
            if method.startswith("x-") or method == "parameters":
                continue
            if not isinstance(spec, dict):
                continue

            summary = spec.get("summary", "")
            description = spec.get("description", "")
            operation_id = spec.get("operationId", "")

            # Search in path, summary, description, operationId
            searchable = f"{path} {summary} {description} {operation_id}".lower()
            if query_lower in searchable:
                results.append(
                    {
                        "path": path,
                        "method": method.upper(),
                        "summary": summary[:100] + "..."
                        if len(summary) > 100
                        else summary,
                        "operationId": operation_id,
                    }
                )

    return results


def get_endpoint(path: str, schema: dict) -> Optional[dict]:
    """Get full specification for a specific endpoint path."""
    paths = schema.get("paths", {})

    # Try exact match first
    if path in paths:
        return {"path": path, "methods": paths[path]}

    # Try with/without leading slash
    alt_path = path if path.startswith("/") else f"/{path}"
    if alt_path in paths:
        return {"path": alt_path, "methods": paths[alt_path]}

    # Try partial match
    for p in paths:
        if path in p:
            return {"path": p, "methods": paths[p]}

    return None


def list_paths(prefix: str, schema: dict) -> list:
    """List all paths, optionally filtered by prefix."""
    paths = schema.get("paths", {})
    result = []

    for path in sorted(paths.keys()):
        if not prefix or path.startswith(prefix):
            methods = [m.upper() for m in paths[path].keys() if not m.startswith("x-")]
            result.append({"path": path, "methods": methods})

    return result


def get_schema_info(schema: dict) -> dict:
    """Get schema metadata and statistics."""
    info = schema.get("info", {})
    paths = schema.get("paths", {})

    # Count methods
    method_counts = {}
    for path_spec in paths.values():
        for method in path_spec.keys():
            if not method.startswith("x-"):
                method_counts[method.upper()] = method_counts.get(method.upper(), 0) + 1

    # Get unique path prefixes (first segment)
    prefixes = set()
    for path in paths.keys():
        parts = path.strip("/").split("/")
        if parts:
            prefixes.add(f"/{parts[0]}")

    return {
        "title": info.get("title"),
        "version": info.get("version"),
        "total_endpoints": len(paths),
        "methods": method_counts,
        "top_level_paths": sorted(prefixes)[:20],
    }


def resolve_ref(ref: str, schema: dict) -> dict:
    """Resolve a $ref pointer to its definition."""
    if not ref.startswith("#/"):
        return {"$ref": ref}  # External ref, can't resolve

    parts = ref[2:].split("/")
    current = schema
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return {"$ref": ref, "_error": "Could not resolve"}
    return current


def expand_endpoint_spec(endpoint: dict, schema: dict, depth: int = 2):
    """Expand $refs in endpoint spec up to a certain depth."""
    if depth <= 0:
        return endpoint

    def expand(obj, d):
        if d <= 0:
            return obj
        if isinstance(obj, dict):
            if "$ref" in obj and len(obj) == 1:
                resolved = resolve_ref(obj["$ref"], schema)
                return expand(resolved, d - 1)
            return {k: expand(v, d) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand(item, d) for item in obj]
        return obj

    return expand(endpoint, depth)


def format_output(data, verbose: bool = False):
    """Format output for display."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "path" in item and "method" in item:
                    print(f"{item['method']:7} {item['path']}")
                    if item.get("summary"):
                        print(f"        {item['summary']}")
                elif "path" in item and "methods" in item:
                    print(f"{item['path']}: {', '.join(item['methods'])}")
                else:
                    print(json.dumps(item, indent=2))
            else:
                print(item)
    elif isinstance(data, dict):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "fetch":
        force = "--force" in sys.argv
        schema = fetch_schema(force=force)
        info = get_schema_info(schema)
        print(f"Schema version: {info['version']}")
        print(f"Total endpoints: {info['total_endpoints']}")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: cf_schema.py search <query>")
            sys.exit(1)
        query = " ".join(sys.argv[2:])
        schema = load_schema()
        results = search_endpoints(query, schema)
        if results:
            print(f"Found {len(results)} matching endpoints:\n")
            format_output(results[:50])  # Limit output
            if len(results) > 50:
                print(f"\n... and {len(results) - 50} more")
        else:
            print(f"No endpoints found matching '{query}'")

    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: cf_schema.py get <path>")
            sys.exit(1)
        path = sys.argv[2]
        schema = load_schema()
        endpoint = get_endpoint(path, schema)
        if endpoint:
            expanded = expand_endpoint_spec(endpoint, schema)
            format_output(expanded)
        else:
            print(f"Endpoint not found: {path}")
            # Suggest similar paths
            paths = list(schema.get("paths", {}).keys())
            similar = [p for p in paths if path.lower() in p.lower()][:5]
            if similar:
                print("\nDid you mean:")
                for p in similar:
                    print(f"  {p}")

    elif cmd == "list":
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        schema = load_schema()
        results = list_paths(prefix, schema)
        format_output(results[:100])
        if len(results) > 100:
            print(f"\n... and {len(results) - 100} more paths")

    elif cmd == "info":
        schema = load_schema()
        info = get_schema_info(schema)
        print(f"Cloudflare API Schema")
        print(f"=====================")
        print(f"Title: {info['title']}")
        print(f"Version: {info['version']}")
        print(f"Total Endpoints: {info['total_endpoints']}")
        print(f"\nMethods:")
        for method, count in sorted(info["methods"].items()):
            print(f"  {method}: {count}")
        print(f"\nTop-level paths:")
        for prefix in info["top_level_paths"]:
            print(f"  {prefix}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
