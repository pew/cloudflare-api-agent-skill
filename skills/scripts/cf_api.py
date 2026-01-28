#!/usr/bin/env python3
"""
Cloudflare API Client - Make authenticated API calls.

Requires CLOUDFLARE_API_TOKEN environment variable (or CLOUDFLARE_API_KEY + CLOUDFLARE_EMAIL).

Usage:
    cf_api.py GET <path>                    # GET request
    cf_api.py POST <path> <json_body>       # POST with JSON body
    cf_api.py PUT <path> <json_body>        # PUT with JSON body
    cf_api.py PATCH <path> <json_body>      # PATCH with JSON body
    cf_api.py DELETE <path>                 # DELETE request
    cf_api.py verify                        # Verify token/credentials

Examples:
    cf_api.py GET /zones
    cf_api.py GET "/zones?name=example.com"
    cf_api.py POST /zones '{"name":"example.com","account":{"id":"..."}}'
    cf_api.py GET /accounts
    cf_api.py verify

Environment Variables:
    CLOUDFLARE_API_TOKEN  - API Token (recommended)
    CLOUDFLARE_API_KEY    - Global API Key (legacy, requires EMAIL)
    CLOUDFLARE_EMAIL      - Account email (only with API_KEY)
    CLOUDFLARE_BASE_URL   - Override API base URL (default: https://api.cloudflare.com/client/v4)
"""

import json
import sys
import os
import urllib.request
import urllib.error
from typing import Optional, Tuple

BASE_URL = os.environ.get("CLOUDFLARE_BASE_URL", "https://api.cloudflare.com/client/v4")


def get_auth_headers() -> dict:
    """Get authentication headers from environment."""
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}

    api_key = os.environ.get("CLOUDFLARE_API_KEY")
    email = os.environ.get("CLOUDFLARE_EMAIL")
    if api_key and email:
        return {"X-Auth-Key": api_key, "X-Auth-Email": email}

    return {}


def check_auth() -> Tuple[bool, str]:
    """Check if authentication is configured."""
    headers = get_auth_headers()
    if not headers:
        return (
            False,
            "No authentication configured. Set CLOUDFLARE_API_TOKEN or (CLOUDFLARE_API_KEY + CLOUDFLARE_EMAIL)",
        )

    if "Authorization" in headers:
        return True, "Using API Token authentication"
    return True, "Using API Key + Email authentication"


def make_request(method: str, path: str, body: Optional[str] = None) -> dict:
    auth_ok, auth_msg = check_auth()
    if not auth_ok:
        return {"success": False, "errors": [{"message": auth_msg}]}

    if path.startswith("http"):
        url = path
    else:
        if not path.startswith("/"):
            path = f"/{path}"
        url = f"{BASE_URL}{path}"

    headers = get_auth_headers()
    headers["Content-Type"] = "application/json"

    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode("utf-8")
            return json.loads(response_data) if response_data else {"success": True}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            return json.loads(error_body)
        except json.JSONDecodeError:
            return {
                "success": False,
                "errors": [
                    {"code": e.code, "message": f"{e.reason}: {error_body[:500]}"}
                ],
            }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "errors": [{"message": f"Connection error: {e.reason}"}],
        }
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def verify_token() -> dict:
    """Verify the API token/credentials work."""
    return make_request("GET", "/user/tokens/verify")


def format_response(response: dict):
    print(json.dumps(response, indent=2))

    if response.get("success"):
        result = response.get("result")
        if isinstance(result, list):
            print(f"\n[Success: {len(result)} items returned]", file=sys.stderr)
        elif isinstance(result, dict) and result.get("id"):
            print(f"\n[Success: ID={result.get('id')}]", file=sys.stderr)
        else:
            print("\n[Success]", file=sys.stderr)
    else:
        errors = response.get("errors", [])
        for err in errors:
            code = err.get("code", "")
            msg = err.get("message", "Unknown error")
            print(f"\n[Error {code}]: {msg}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].upper()

    if cmd == "VERIFY":
        auth_ok, auth_msg = check_auth()
        print(auth_msg)
        if auth_ok:
            result = verify_token()
            format_response(result)
        sys.exit(0 if auth_ok else 1)

    if cmd not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        print(f"Unknown method: {cmd}")
        print("Supported methods: GET, POST, PUT, PATCH, DELETE, VERIFY")
        sys.exit(1)

    if len(sys.argv) < 3:
        print(f"Usage: cf_api.py {cmd} <path> [json_body]")
        sys.exit(1)

    path = sys.argv[2]
    body = sys.argv[3] if len(sys.argv) > 3 else None

    if body:
        try:
            json.loads(body)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON body: {e}", file=sys.stderr)
            sys.exit(1)

    result = make_request(cmd, path, body)
    format_response(result)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
