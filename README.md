# Cloudflare API Agent Skill

This aims to be an [Agent Skill](https://agentskills.io/home) for the Cloudflare API. It fetches and caches the OpenAPI schema for endpoint discovery and documentation.

## Setup

To use this skill, you need to set the `CLOUDFLARE_API_TOKEN` environment variable. An read-only token works fine if you only need to read data.

```
export CLOUDFLARE_API_TOKEN="your-token-here"
```

Create tokens at: [https://dash.cloudflare.com/?to=/:account/api-tokens](https://dash.cloudflare.com/?to=/:account/api-tokens)

## Examples

**List DNS records:**

```
list all my cloudflare dns records for example.com
```

**List Load Balancers:**

```
list all my cloudflare load balancers for example.com
```
