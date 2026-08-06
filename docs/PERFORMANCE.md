# JobPilot AI — Performance & Scalability Guide

This document maps the requested optimization checklist to concrete implementations in the repo.

## Frontend

| Technique | Implementation |
|-----------|----------------|
| Route-based lazy loading / dynamic imports / code splitting | `src/routes/AppRouter.tsx` (`React.lazy`) |
| Suspense + skeleton loaders | `PageSuspense`, `PageSkeleton` |
| Concurrent rendering | `startTransition` on navigation |
| React.memo / useMemo / useCallback | Jobs page, layout nav, virtualized rows, images |
| Debouncing / throttling | `useDebouncedValue`, `debounce`, `throttle`, `useThrottleCallback` |
| Virtualization | `react-window` via `VirtualizedJobList` |
| Infinite scrolling + pagination | `useInfiniteQuery` on Jobs page |
| Optimistic UI | TanStack Query `onMutate` for track/apply |
| Prefetching | `PrefetchContext` on nav hover |
| API caching | TanStack Query `staleTime` / `gcTime` |
| Memoized selectors | `store/selectors/*` (`createSelector`) |
| Avoid prop drilling | Redux + Prefetch Context |
| Proper keys / avoid anonymous handlers | stable `key={id}`, memoized action cells |
| Image optimization | `OptimizedImage` (lazy, decode=async, skeleton) |
| Tree shaking / bundle splitting / minification | Vite `manualChunks`, `minify: esbuild` |
| Gzip/Brotli | `vite-plugin-compression` + nginx `gzip_static` |
| CDN static assets | long-cache hashed assets in `nginx.conf` |

### SSR / SSG / ISR

The app is a **Vite SPA**. The production shell is statically generated and served from nginx/CDN (SSG of the SPA shell). Full React SSR/ISR would require Next.js/Remix or Vite SSR — see migration note in Deployment. Prefetch + HTTP caching approximate ISR for API-driven views.

## Backend (FastAPI)

| Technique | Implementation |
|-----------|----------------|
| Async endpoints + Motor async driver | All routers/services |
| Connection pooling | Mongo `maxPoolSize` / Redis `ConnectionPool` |
| Dependency injection | `dependencies/services.py`, auth deps |
| Background tasks | Kafka workers + Celery (`workers/celery_app.py`) |
| Kafka async processing | fetch/match/apply/notify/report workers |
| GZipMiddleware | `main.py` |
| ORJSON responses | `default_response_class=ORJSONResponse` |
| Rate limiting | Redis sliding window Lua |
| Request validation | Pydantic v2 schemas |
| Pagination / filtering / sorting / field selection | `utils/pagination.py`, job filters |
| Selective projection / bulk ops | `BaseRepository.find_projected`, `bulk_insert`, `bulk_update` |
| Streaming CSV / file streaming | `utils/streaming.py` |
| HTTP caching ETag / Cache-Control | `middleware/http_cache.py` |
| Idempotency | `Idempotency-Key` middleware |
| Retry + circuit breaker | `core/resilience.py` |
| Token blacklisting | Redis `auth:blacklist:{jti}` |
| OpenTelemetry | `core/telemetry.py` (optional) |
| Health / ready / metrics | `/health`, `/health/ready`, `/metrics` |
| Graceful shutdown | lifespan teardown order |
| Gunicorn + Uvicorn workers | `gunicorn.conf.py` |
| HTTP Keep-Alive | gunicorn `keepalive` + nginx HTTP/1.1 |
| API versioning | `/api/v1` prefix |

## Redis patterns

| Pattern | Location |
|---------|----------|
| Cache Aside / Read Through | `CacheService.get_or_set` / `read_through` |
| Write Through / Write Behind | `write_through` / `write_behind` |
| TTL + Sliding expiration | `set_sliding` / `get_sliding` |
| Invalidation / Warming / Pipeline | `invalidate*`, `warm`, `pipeline_set_many` |
| Key namespacing | `core/redis.ns` |
| Distributed locks (Lua) | `DistributedLock` |
| Rate limiting (Lua) | `rate_limit_allow` |
| Pub/Sub, Streams | `publish`, `stream_add` |
| Leaderboards / counters | Sorted sets + `incr_counter` |
| Session storage | `set_session` / `get_session` |
| HyperLogLog / Geo / Bloom approx | `hll_*`, `geo_*`, `bloom_*` |
| Memory eviction | configure Redis `maxmemory-policy allkeys-lru` in ops |

## Database

- Indexes defined on Beanie models (composite user/status, match_score, portal+external_id)
- Connection pooling via Motor
- Projection & batch APIs for heavy reads/writes
- Pagination everywhere for list endpoints
- Read-replica / sharding / partitioning: deploy-time Mongo topology (documented in `DEPLOYMENT.md`)

## Production process model

```bash
# API
gunicorn app.main:app -c gunicorn.conf.py

# Celery
celery -A app.workers.celery_app.celery_app worker -l info

# Kafka workers (existing)
python -m app.workers.fetch_worker
```
