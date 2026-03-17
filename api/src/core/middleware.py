# Core — middleware pipeline (order: logging -> CORS -> tenant scoping -> rate limit)
# TenantScopingMiddleware: extracts tenant_id from session cookie, injects into request.state
# RateLimitMiddleware: Redis sliding window, 100 req/min default, 10 req/min on /auth/login
