from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from contextvars import ContextVar
from collections import Counter, defaultdict, OrderedDict
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpcore
import httpx

from .models import utcnow
from .store import Store

USER_AGENT = "SignalpostResearch/1.0 (public company research; robots respected)"
DENIED_HOSTS = ("linkedin.com", "facebook.com", "instagram.com", "glassdoor.com", "indeed.com", "google.com", "google.no", "bing.com", "tiktok.com", "x.com", "twitter.com")
REQUEST_SCOPE = ContextVar("request_scope", default=None)


class FetchError(Exception):
    def __init__(self, state: str, reason: str, snapshot=None):
        super().__init__(reason)
        self.state = state
        self.snapshot = snapshot


def safe_url(url: str) -> str:
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 32 for c in url) or "\\" in url:
        raise FetchError("blocked", "Unsafe URL syntax")
    try:
        p = urlsplit(url)
        host = (p.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        if p.scheme not in {"http", "https"} or not host or p.username or p.password or p.port not in {None, 80, 443}:
            raise ValueError()
        if host in {"localhost", "metadata.google.internal"} or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError()
        if any(host == h or host.endswith("." + h) for h in DENIED_HOSTS):
            raise ValueError()
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None
        if ip is not None and not ip.is_global:
            raise ValueError()
        netloc = f"[{host}]" if ":" in host else host
        if p.port:
            netloc += f":{p.port}"
        return urlunsplit((p.scheme, netloc, p.path or "/", p.query, ""))
    except (ValueError, UnicodeError):
        raise FetchError("blocked", "URL policy: public HTTP(S), no credentials, standard ports, permitted hosts only") from None


async def resolve_public(host: str, port: int) -> list[str]:
    records = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = sorted({r[4][0] for r in records})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise FetchError("blocked", "DNS resolved to non-public address")
    return addresses


class PinnedBackend(httpcore.AsyncNetworkBackend):
    """Resolve, validate, and connect to the same IP; TLS keeps the original hostname.

    httpcore 1.0.9's connection pool supplies the hostname separately for start_tls.
    No proxy, alternate DNS connection, Unix socket, automatic redirect or transport retry.
    """
    def __init__(self):
        self.inner = httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        host = host.decode() if isinstance(host, bytes) else host
        addresses = await resolve_public(host, port)
        return await self.inner.connect_tcp(addresses[0], port, timeout, local_address, socket_options)

    async def connect_unix_socket(self, *args, **kwargs):
        raise FetchError("blocked", "Unix sockets forbidden")

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)


class Budget:
    def __init__(self, max_requests=2000, max_seconds=2700.0, margin=5.0):
        self.max_requests = max_requests
        self.max_seconds = max_seconds
        self.started = time.monotonic()
        self.deadline = self.started + max(0, max_seconds - min(margin, max_seconds / 10))
        self.requests = 0
        self.bytes = 0
        self.failures = Counter()
        self.cache_hits = 0
        self.latencies = []
        self.by_host = Counter()
        self.by_company = Counter()
        self.on_take = None

    def check_time(self):
        if time.monotonic() >= self.deadline:
            raise FetchError("failed", "Time budget exhausted; source not checked")

    def check(self):
        self.check_time()
        if self.requests >= self.max_requests:
            raise FetchError("failed", "Request budget exhausted; source not checked")

    def take(self, host):
        self.check()
        scope = REQUEST_SCOPE.get()
        if scope:
            if scope["used"] >= scope["allowance"]:
                raise FetchError("failed", "Company request allocation exhausted; source not checked")
            scope["used"] += 1
            self.by_company[scope["org"]] += 1
        self.requests += 1
        self.by_host[host] += 1
        if self.on_take:
            self.on_take(self.requests, host, scope["org"] if scope else None)

    @property
    def remaining(self):
        return max(0, self.max_requests - self.requests)

    def report(self):
        values = sorted(self.latencies)
        return {"requests": self.requests, "bytes": self.bytes, "runtime_ms": round((time.monotonic() - self.started) * 1000),
                "third_party_cost_usd": 0, "api_usage": {"documented_brreg_http_starts": self.by_host.get("data.brreg.no", 0), "paid_api_calls": 0, "model_calls": 0}, "cache_hits": self.cache_hits,
                "source_failures": dict(self.failures), "requests_by_host": dict(self.by_host),
                "requests_by_company": dict(self.by_company),
                "request_p50_ms": values[len(values) // 2] if values else None,
                "request_p95_ms": values[min(len(values) - 1, int(len(values) * .95))] if values else None}


@dataclass
class Result:
    snapshot: dict
    data: bytes
    root_path: str = ""
    document: object = None

    def json(self):
        if self.document is None:
            self.document=json.loads(self.data)
        value = self.document
        for token in self.root_path.strip('/').split('/') if self.root_path else []:
            token = token.replace('~1','/').replace('~0','~')
            value = value[int(token)] if isinstance(value,list) else value[token]
        return value


class Fetcher:
    def __init__(self, store: Store, budget: Budget, *, transport=None, timeout_seconds=15.0):
        self.store, self.budget = store, budget
        self.timeout_seconds=min(120.0,max(.1,float(timeout_seconds)))
        if transport is None:
            transport = httpx.AsyncHTTPTransport(retries=0, limits=httpx.Limits(max_connections=16, max_keepalive_connections=8))
            transport._pool._network_backend = PinnedBackend()
        self.client = httpx.AsyncClient(transport=transport, follow_redirects=False, trust_env=False,
                                        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,text/plain;q=0.9,*/*;q=0.1", "Accept-Encoding": "identity"})
        self.locks = defaultdict(asyncio.Lock)
        self.next_time = defaultdict(float)
        self.cooldowns = defaultdict(float)
        self.consecutive = Counter()
        self.robots = {}
        self.robot_locks = defaultdict(asyncio.Lock)
        self.events = []
        self.responses = OrderedDict()
        self.response_locks = defaultdict(asyncio.Lock)
        self.shared_hits = 0

    async def close(self):
        await self.client.aclose()

    async def _request(self, url: str, headers: dict, limit: int) -> tuple[int, dict, bytes]:
        host = urlsplit(url).hostname
        async with self.locks[host]:
            self.budget.check()
            if self.cooldowns[host] and time.monotonic() >= self.cooldowns[host]:
                self.consecutive[host] = 0
                self.cooldowns[host] = 0
            if time.monotonic() < self.cooldowns[host]:
                if host == 'data.brreg.no':
                    # A shared official-source cooldown must not instantly fail
                    # every later company. Wait politely inside the global wall
                    # cap; never bypass the source's Retry-After/circuit interval.
                    await asyncio.sleep(min(self.cooldowns[host]-time.monotonic(),max(0,self.budget.deadline-time.monotonic())))
                    self.budget.check()
                    self.cooldowns[host]=0
                    self.consecutive[host]=0
                else:
                    raise FetchError("blocked", "Host circuit breaker/cooldown open; no request attempted")
            delay = self.next_time[host] - time.monotonic()
            if delay > 0:
                await asyncio.sleep(min(delay, max(0, self.budget.deadline - time.monotonic())))
            self.budget.take(host)
            started = time.monotonic()
            self.next_time[host] = started + (0.25 if host == "data.brreg.no" else 1.0)
            event = {"url": url, "started_at": utcnow(), "request_number": self.budget.requests}
            if REQUEST_SCOPE.get():
                event["organisation_number"] = REQUEST_SCOPE.get()["org"]
                event['module']=REQUEST_SCOPE.get().get('module','registry')
            try:
                timeout = min(self.timeout_seconds, max(.01, self.budget.deadline - time.monotonic()))
                async with asyncio.timeout(timeout):
                    async with self.client.stream("GET", url, headers=headers, timeout=timeout) as r:
                        # Avoid decoder expansion bombs: request identity and reject
                        # a server that still applies content compression. Compressed
                        # development bulk files are separately streamed from fixed APIs.
                        if r.headers.get("content-encoding", "identity").lower() not in {"identity", ""}:
                            raise FetchError("failed", "Unexpected content compression; safe bounded download refused")
                        data = bytearray()
                        async for chunk in r.aiter_bytes(chunk_size=65536):
                            self.budget.bytes += len(chunk)
                            if len(data) + len(chunk) > limit:
                                raise FetchError("failed", "Response exceeded bounded download limit")
                            data.extend(chunk)
                        status, response_headers = r.status_code, dict(r.headers)
                event["status"] = status
                if status == 429:
                    try:
                        retry = min(120, max(5, float(response_headers.get("retry-after", "30"))))
                    except ValueError:
                        retry = 60
                    self.cooldowns[host] = time.monotonic() + retry
                if status >= 500:
                    self.consecutive[host] += 1
                    if self.consecutive[host] >= 5:
                        self.cooldowns[host] = time.monotonic() + 30
                else:
                    self.consecutive[host] = 0
                return status, response_headers, bytes(data)
            except FetchError:
                raise
            except (httpx.HTTPError, OSError, TimeoutError) as exc:
                self.consecutive[host] += 1
                if self.consecutive[host] >= 5:
                    self.cooldowns[host] = time.monotonic() + 30
                event["error"] = type(exc).__name__
                raise FetchError("failed", f"Public source request failed: {type(exc).__name__}") from None
            finally:
                event["elapsed_ms"] = round((time.monotonic() - started) * 1000)
                self.budget.latencies.append(event["elapsed_ms"])
                self.events.append(event)

    async def allowed(self, url: str):
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        async with self.robot_locks[origin]:
            if origin not in self.robots:
                try:
                    result = await self.get(origin + "/robots.txt", "robots", robots=False, limit=256_000,attempts=1)
                    status = result.snapshot["http_status"]
                    if status in {404, 410}:
                        self.robots[origin] = None
                    elif status in {200, 204, 304}:
                        rp = RobotFileParser()
                        rp.parse(result.data.decode("utf-8", "replace").splitlines())
                        self.robots[origin] = rp
                        final = urlsplit(result.snapshot['final_url'])
                        if final.path == '/robots.txt':
                            self.robots.setdefault(f'{final.scheme}://{final.netloc}', rp)
                    else:
                        raise FetchError("blocked", "Robots policy unavailable")
                except FetchError as exc:
                    self.robots[origin] = exc
            rp = self.robots[origin]
        if isinstance(rp, FetchError):
            raise FetchError(rp.state, "Robots check failed: " + str(rp), rp.snapshot)
        if rp is not None:
            if not rp.can_fetch(USER_AGENT, url):
                raise FetchError("blocked", "Robots policy disallows this URL")
            delay = rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*")
            if delay:
                host = p.hostname
                self.next_time[host] = max(self.next_time[host], time.monotonic() + min(delay, 120))

    async def get(self, url: str, source_class: str, *, robots=True, limit=2_000_000, attempts=2) -> Result:
        original = safe_url(url)
        # Only this invocation's genuinely fetched responses. New runs still make
        # live/conditional requests; no undeclared persistent warm cache is used.
        key = (original, robots, limit)
        async with self.response_locks[key]:
            if key in self.responses:
                self.shared_hits += 1
                result = self.responses[key]
                if isinstance(result, FetchError):
                    raise FetchError(result.state, str(result), result.snapshot)
                return result
            try:
                result = await self._get(original, source_class, robots=robots, limit=limit, attempts=attempts)
            except FetchError as exc:
                # Policy blocks/absent sites may be shared; don't turn a budget
                # failure for one company into a cached failure for another.
                if exc.state == 'blocked':
                    self.responses[key] = exc
                raise
            self.responses[key] = result
            while len(self.responses) > 128:
                self.responses.popitem(last=False)
            return result

    async def _get(self, url: str, source_class: str, *, robots=True, limit=2_000_000, attempts=2) -> Result:
        original = safe_url(url)
        current, chain = original, []
        for hop in range(6):
            current = safe_url(current)
            if robots:
                await self.allowed(current)
            cached = self.store.cache(current)
            headers = {}
            if cached:
                if cached["etag"]:
                    headers["If-None-Match"] = cached["etag"]
                if cached["modified"]:
                    headers["If-Modified-Since"] = cached["modified"]
            for attempt in range(attempts):
                try:
                    status, response_headers, data = await self._request(current, headers, limit)
                    if status in {502, 503, 504} and attempt + 1 < attempts:
                        await asyncio.sleep(.5)
                        continue
                    break
                except FetchError as exc:
                    if exc.state != "failed" or "budget" in str(exc) or attempt + 1 == attempts:
                        self.budget.failures[str(exc)] += 1
                        raise
            if status in {301, 302, 303, 307, 308}:
                if not response_headers.get("location"):
                    raise FetchError("failed", "Redirect omitted destination")
                chain.append({"url": current, "status": status})
                current = safe_url(urljoin(current, response_headers["location"]))
                continue
            checked_at = utcnow()
            if status == 304:
                if not cached:
                    raise FetchError("failed", "304 without prior collected evidence")
                data = (self.store.root / cached["snapshot"]["storage_ref"]).read_bytes()
                self.budget.cache_hits += 1
            meta = {"source_url": original, "final_url": current, "source_class": source_class,
                    "retrieved_at": checked_at, "source_published_at": None, "http_last_modified": response_headers.get("last-modified"),
                    "http_status": status, "redirect_chain": chain, "revalidated": status == 304,
                    "content_type": response_headers.get("content-type", (cached or {}).get("snapshot", {}).get("content_type", ""))}
            snapshot = self.store.snapshot(meta, data)
            if status in {200, 304}:
                self.store.set_cache(current, snapshot, {"etag": response_headers.get("etag") or (cached or {}).get("etag"),
                                                       "last-modified": response_headers.get("last-modified") or (cached or {}).get("modified")})
            if status in {401, 403, 429, 451}:
                self.budget.failures[f"HTTP {status}"] += 1
                raise FetchError("blocked", f"HTTP {status}; no bypass attempted", snapshot)
            if status >= 400 and status not in {404, 410}:
                self.budget.failures[f"HTTP {status}"] += 1
                raise FetchError("failed", f"HTTP {status}", snapshot)
            return Result(snapshot, data)
        raise FetchError("failed", "Redirect limit exceeded")
