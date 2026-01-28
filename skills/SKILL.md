---
name: cloudflare-api
description: Cloudflare API integration for zones, DNS, Workers, Pages, R2, KV, and all Cloudflare services. Use when users ask about Cloudflare resources, need to query/modify DNS records, manage zones, deploy Workers/Pages, configure CDN settings, or interact with any Cloudflare service. Triggers on mentions of Cloudflare, DNS management, CDN configuration, edge computing, or specific services like R2, KV, Workers, Pages, WAF, etc.
---

# Cloudflare API

## Overview

Tools to discover, understand, and call Cloudflare APIs. The OpenAPI schema (~8MB, 1600+ endpoints) is fetched dynamically and cached locally, ensuring you always work with the latest API definitions.

## Quick Reference

| Task | Command |
|------|---------|
| Find endpoints | `cf_schema.py search "<keyword>"` |
| Get endpoint spec | `cf_schema.py get "<path>"` |
| List all paths | `cf_schema.py list [prefix]` |
| Schema stats | `cf_schema.py info` |
| Make API call | `cf_api.py <METHOD> <path> [body]` |
| Verify auth | `cf_api.py verify` |

## Authentication

```bash
# Recommended: API Token (scoped permissions)
export CLOUDFLARE_API_TOKEN="your-token-here"

# Legacy: Global API Key (full account access)
export CLOUDFLARE_API_KEY="your-key"
export CLOUDFLARE_EMAIL="your-email"
```

Create API tokens at: https://dash.cloudflare.com/profile/api-tokens

## Workflow

### 1. Discover Endpoints

```bash
python3 scripts/cf_schema.py search "dns record"
python3 scripts/cf_schema.py search "worker"
python3 scripts/cf_schema.py list /zones
```

### 2. Get Endpoint Details

```bash
python3 scripts/cf_schema.py get "/zones/{zone_id}/dns_records"
```

### 3. Make API Calls

```bash
python3 scripts/cf_api.py verify
python3 scripts/cf_api.py GET /zones
python3 scripts/cf_api.py GET "/zones?name=example.com"
python3 scripts/cf_api.py POST /zones/{zone_id}/dns_records '{"type":"A","name":"www","content":"1.2.3.4"}'
python3 scripts/cf_api.py DELETE /zones/{zone_id}/dns_records/{id}
```

## Common Patterns

### Get Zone ID

```bash
python3 scripts/cf_api.py GET "/zones?name=example.com"
```

### DNS Records

```bash
python3 scripts/cf_api.py GET /zones/{zone_id}/dns_records
python3 scripts/cf_api.py POST /zones/{zone_id}/dns_records '{"type":"A","name":"www","content":"192.0.2.1","ttl":3600,"proxied":true}'
python3 scripts/cf_api.py PATCH /zones/{zone_id}/dns_records/{record_id} '{"content":"192.0.2.2"}'
```

### Workers & Pages

```bash
python3 scripts/cf_api.py GET /accounts/{account_id}/workers/scripts
python3 scripts/cf_api.py GET /accounts/{account_id}/pages/projects
```

## Top-Level API Areas

| Prefix | Description |
|--------|-------------|
| `/zones` | Zone management, DNS, SSL, caching, firewall |
| `/accounts` | Workers, Pages, R2, KV, Images |
| `/user` | User profile, tokens |

## Response Format

```json
{
  "success": true,
  "errors": [],
  "messages": [],
  "result": { ... },
  "result_info": { "page": 1, "per_page": 20, "total_count": 100 }
}
```

## Tips

1. Schema is cached 24h - use `cf_schema.py fetch --force` to refresh
2. Most zone operations need `{zone_id}` from `/zones` list
3. Account resources (Workers, R2, KV) need `{account_id}` from `/accounts`
4. Rate limit: 1200 req/5min (check `X-RateLimit-Remaining` header)
