#!/usr/bin/env python
"""
Douyin creator commerce tracker.

This tool connects to an already-running Google Chrome through CDP. It does not
launch Chrome through Playwright or create a Playwright browser instance.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
import traceback
import base64
import ctypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import parse, request

import websocket
from openpyxl import Workbook


DEFAULT_PROFILE_URL = "https://v.douyin.com/yrNAdFgturw/"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_PATH = PROJECT_DIR / "outputs" / "douyin_creator_tracker.xlsx"
DEFAULT_EVIDENCE_DIR = PROJECT_DIR / "evidence" / "run"
DEFAULT_INCREMENTAL_DB = PROJECT_DIR / "outputs" / "collected_index.json"
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040
JSON_URL_KEYWORDS = (
    "aweme",
    "post",
    "item",
    "detail",
    "product",
    "ecom",
    "shop",
    "promotion",
    "commodity",
    "sku",
)

PRODUCT_ID_KEYS = (
    "product_id",
    "productId",
    "productID",
    "commodity_id",
    "commodityId",
    "goods_id",
    "goodsId",
    "shop_goods_id",
    "shopGoodsId",
    "promotion_id",
    "promotionId",
    "promotionID",
    "ec_promotion_id",
    "ecPromotionId",
)
PRODUCT_NAME_KEYS = (
    "product_name",
    "productName",
    "commodity_name",
    "commodityName",
    "goods_name",
    "goodsName",
    "promotion_name",
    "promotionName",
    "short_title",
    "shortTitle",
    "title",
    "name",
)
PRODUCT_URL_KEYS = (
    "product_url",
    "productUrl",
    "detail_url",
    "detailUrl",
    "schema",
    "jump_url",
    "jumpUrl",
    "url",
    "h5_url",
    "h5Url",
)


HEADERS = [
    "creator_name",
    "creator_profile_url",
    "source_profile_url",
    "video_id",
    "video_url",
    "video_title",
    "publish_time",
    "has_product",
    "product_name",
    "product_id",
    "product_url",
    "collect_time",
    "collect_status",
    "error_message",
]


class CdpError(RuntimeError):
    pass


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def human_pause(enabled: bool, min_seconds: float, max_seconds: float, log=None, reason: str = "pause") -> None:
    if not enabled:
        return
    seconds = random.uniform(min_seconds, max_seconds)
    if log:
        log(f"humanize {reason}: sleep {seconds:.1f}s")
    time.sleep(seconds)


def request_keep_awake(log=None) -> bool:
    if os.name != "nt":
        return False
    try:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
        if log:
            log("keep-awake enabled with SetThreadExecutionState")
        return True
    except Exception as exc:
        if log:
            log(f"keep-awake enable failed: {exc}")
        return False


def clear_keep_awake(log=None) -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        if log:
            log("keep-awake cleared")
    except Exception as exc:
        if log:
            log(f"keep-awake clear failed: {exc}")


def start_keep_awake_thread(enabled: bool, log=None) -> threading.Event:
    stop_event = threading.Event()
    if not enabled:
        return stop_event

    def loop() -> None:
        while not stop_event.is_set():
            request_keep_awake(log)
            stop_event.wait(45)

    thread = threading.Thread(target=loop, name="keep-awake", daemon=True)
    thread.start()
    return stop_event


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def http_json(url: str, method: str = "GET") -> Any:
    req = request.Request(url, method=method)
    opener = request.build_opener(request.ProxyHandler({}))
    with opener.open(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def http_text(url: str, method: str = "GET") -> str:
    req = request.Request(url, method=method)
    opener = request.build_opener(request.ProxyHandler({}))
    with opener.open(req, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize_cdp_url(url: str) -> str:
    return url.rstrip("/")


def find_video_id(url: str, text: str = "") -> str:
    joined = f"{url} {text}"
    patterns = [
        r"/video/(\d+)",
        r"modal_id=(\d+)",
        r"aweme_id=(\d+)",
        r"item_id=(\d+)",
        r"video_id=(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, joined)
        if m:
            return m.group(1)
    return ""


def find_product_id(url: str, text: str = "") -> str:
    joined = f"{url} {text}"
    patterns = [
        r"product_id[=/:%3D]+(\d+)",
        r"promotion_id[=/:%3D]+(\d+)",
        r"ec_promotion_id[=/:%3D]+(\d+)",
        r"promotion_ids[=/:%3D]+(\d+)",
        r"commodity_id[=/:%3D]+(\d+)",
        r"goods_id[=/:%3D]+(\d+)",
        r"/product/(\d+)",
    ]
    decoded = parse.unquote(joined)
    for target in (joined, decoded):
        for pattern in patterns:
            m = re.search(pattern, target, re.IGNORECASE)
            if m and len(m.group(1)) >= 8:
                return m.group(1)
    return ""


def clean_text(value: Any, max_len: int = 300) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:max_len]


def looks_like_product_url(url: str) -> bool:
    lower = (url or "").lower()
    return bool(
        re.search(r"(^|[/?&._=-])(product|product_id|promotion_id|commodity_id|goods_id|shop_goods_id|sku)([/?&._=-]|$)", lower)
        or "/product/" in lower
        or "/shop/" in lower
    )


def looks_like_product_name(name: str) -> bool:
    name = clean_text(name, 180)
    if not name or name in {"推荐", "首页", "搜索", "关注", "朋友", "我的", "直播", "更多", "登录"}:
        return False
    return bool(re.search(r"(孕妇|裤|裙|衣|装|鞋|包|内衣|托腹|凉感|休闲|长裤|短裤|商品)", name))


def is_valid_product(product: "ProductInfo") -> bool:
    has_id = bool(valid_product_id(product.product_id))
    has_url = looks_like_product_url(product.product_url)
    return bool(has_id or has_url)


def looks_like_json_url(url: str) -> bool:
    lower = url.lower()
    return any(word in lower for word in JSON_URL_KEYWORDS)


@dataclass
class VideoCandidate:
    video_id: str
    video_url: str
    title_hint: str


@dataclass
class ProductInfo:
    product_name: str = ""
    product_id: str = ""
    product_url: str = ""


class CdpPage:
    def __init__(self, ws_url: str, log_path: Path):
        self.ws_url = ws_url
        self.log_path = log_path
        os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
        os.environ.setdefault("no_proxy", "127.0.0.1,localhost")
        self.ws = websocket.create_connection(ws_url, timeout=10, http_proxy_host=None, suppress_origin=True)
        self.next_id = 0
        self.pending: dict[int, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.stop = False
        self.finished_requests: list[tuple[str, str]] = []
        self.request_urls: dict[str, str] = {}
        self.receiver = threading.Thread(target=self._recv_loop, daemon=True)
        self.receiver.start()

    def log(self, message: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{now_text()}] {message}\n")

    def close(self) -> None:
        self.stop = True
        try:
            self.ws.close()
        except Exception:
            pass

    def _recv_loop(self) -> None:
        while not self.stop:
            try:
                raw = self.ws.recv()
                if not raw:
                    continue
                msg = json.loads(raw)
            except Exception:
                if not self.stop:
                    self.log("CDP receive loop stopped unexpectedly")
                return

            if "id" in msg:
                req_id = msg["id"]
                box = self.pending.get(req_id)
                if box is not None:
                    box["response"] = msg
                    box["event"].set()
                continue

            method = msg.get("method")
            params = msg.get("params", {})
            if method == "Network.responseReceived":
                response = params.get("response", {})
                req_id = params.get("requestId", "")
                url = response.get("url", "")
                mime = response.get("mimeType", "")
                if req_id and looks_like_json_url(url):
                    self.request_urls[req_id] = url
                elif req_id and ("json" in mime.lower()):
                    self.request_urls[req_id] = url
            elif method == "Network.loadingFinished":
                req_id = params.get("requestId", "")
                url = self.request_urls.get(req_id, "")
                if req_id and url:
                    self.finished_requests.append((req_id, url))

    def call(self, method: str, params: dict[str, Any] | None = None, timeout: float = 15) -> Any:
        with self.lock:
            self.next_id += 1
            req_id = self.next_id
        box = {"event": threading.Event(), "response": None}
        self.pending[req_id] = box
        payload = {"id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.ws.send(json.dumps(payload))
        if not box["event"].wait(timeout):
            self.pending.pop(req_id, None)
            raise CdpError(f"CDP timeout: {method}")
        self.pending.pop(req_id, None)
        response = box["response"]
        if response and response.get("error"):
            raise CdpError(f"{method}: {response['error']}")
        return response.get("result") if response else None

    def setup(self) -> None:
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.set_window_bounds()

    def set_window_bounds(self, width: int = 1280, height: int = 920) -> None:
        try:
            target = self.call("Target.getTargetInfo")
            target_id = target.get("targetInfo", {}).get("targetId")
            if not target_id:
                return
            window = self.call("Browser.getWindowForTarget", {"targetId": target_id})
            window_id = window.get("windowId")
            if window_id is None:
                return
            self.call("Browser.setWindowBounds", {"windowId": window_id, "bounds": {"width": width, "height": height}})
        except Exception as exc:
            self.log(f"set_window_bounds skipped: {exc}")

    def navigate(self, url: str, wait_seconds: float = 4) -> None:
        self.call("Page.navigate", {"url": url})
        self.wait_ready(timeout=max(10, wait_seconds + 6))
        time.sleep(wait_seconds)

    def wait_ready(self, timeout: float = 20) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                state = self.eval("document.readyState")
                if state in ("interactive", "complete"):
                    return
            except Exception:
                pass
            time.sleep(0.25)

    def eval(self, expression: str, timeout: float = 15) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "userGesture": True,
            },
            timeout=timeout,
        )
        remote = result.get("result", {})
        if "value" in remote:
            return remote.get("value")
        if "description" in remote:
            return remote.get("description")
        return None

    def current_url(self) -> str:
        return self.eval("location.href") or ""

    def screenshot(self, path: Path) -> None:
        try:
            data = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            import base64

            path.write_bytes(base64.b64decode(data["data"]))
        except Exception as exc:
            self.log(f"failed to write screenshot {path}: {exc}")

    def drain_json_payloads(self, max_items: int = 80) -> list[tuple[str, Any]]:
        items: list[tuple[str, Any]] = []
        seen: set[str] = set()
        while self.finished_requests and len(items) < max_items:
            req_id, url = self.finished_requests.pop(0)
            if req_id in seen:
                continue
            seen.add(req_id)
            try:
                body = self.call("Network.getResponseBody", {"requestId": req_id}, timeout=5)
            except Exception:
                continue
            raw = body.get("body", "") if body else ""
            if not raw or len(raw) > 4_000_000:
                continue
            if body.get("base64Encoded"):
                continue
            parsed = parse_jsonish(raw)
            if parsed is not None:
                items.append((url, parsed))
        return items


def parse_jsonish(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    if text.startswith(")]}'"):
        text = text.split("\n", 1)[-1]
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def parse_embedded_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if len(text) < 2 or len(text) > 200_000:
        return value
    if not ((text[0] == "{" and text[-1] == "}") or (text[0] == "[" and text[-1] == "]")):
        decoded = parse.unquote(text)
        if decoded == text or not (
            (decoded.startswith("{") and decoded.endswith("}")) or (decoded.startswith("[") and decoded.endswith("]"))
        ):
            return value
        text = decoded
    try:
        return json.loads(text)
    except Exception:
        return value


def load_har_payloads(har_path: Path) -> list[tuple[str, Any]]:
    data = json.loads(har_path.read_text(encoding="utf-8", errors="replace"))
    entries = data.get("log", {}).get("entries", [])
    payloads: list[tuple[str, Any]] = []
    for entry in entries:
        request_info = entry.get("request", {})
        response_info = entry.get("response", {})
        url = request_info.get("url", "") or response_info.get("url", "")
        if not looks_like_json_url(url):
            continue
        content = response_info.get("content", {})
        text = content.get("text", "")
        if text and content.get("encoding") == "base64":
            try:
                text = base64.b64decode(text).decode("utf-8", errors="replace")
            except Exception:
                text = ""
        parsed = parse_jsonish(text) if text else None
        if parsed is not None:
            payloads.append((url, parsed))
        post_text = request_info.get("postData", {}).get("text", "")
        post_parsed = parse_jsonish(post_text) if post_text else None
        if post_parsed is not None:
            payloads.append((url + " [request]", post_parsed))
    return payloads


def connect_or_create_tab(cdp_url: str, initial_url: str, log_path: Path) -> CdpPage:
    cdp_url = normalize_cdp_url(cdp_url)
    try:
        version = http_json(f"{cdp_url}/json/version")
    except Exception as exc:
        raise CdpError(
            "Cannot connect to Chrome CDP. Start Chrome first, for example: "
            r'chrome.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" --profile-directory="Default"'
        ) from exc

    browser_name = version.get("Browser", "")
    if "Chrome" not in browser_name:
        raise CdpError(f"CDP endpoint is not Google Chrome: {browser_name}")

    targets = http_json(f"{cdp_url}/json/list")
    pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    target = None
    if pages:
        douyin_pages = [t for t in pages if "douyin.com" in (t.get("url") or "")]
        user_pages = [t for t in douyin_pages if "/user/" in (t.get("url") or "")]
        target = (user_pages or douyin_pages or pages)[0]
    if target is None:
        encoded = parse.quote(initial_url, safe="")
        target = http_json(f"{cdp_url}/json/new?{encoded}", method="PUT")
    ws_url = target.get("webSocketDebuggerUrl")
    if not ws_url:
        raise CdpError("Chrome CDP target has no webSocketDebuggerUrl")
    page = CdpPage(ws_url, log_path)
    page.setup()
    return page


def close_extra_douyin_tabs(cdp_url: str, keep_url_hint: str = "", max_tabs: int = 3, log=None) -> None:
    cdp_url = normalize_cdp_url(cdp_url)
    try:
        targets = http_json(f"{cdp_url}/json/list")
    except Exception as exc:
        if log:
            log(f"close_extra_tabs skipped: {exc}")
        return
    pages = [t for t in targets if t.get("type") == "page" and "douyin.com" in (t.get("url") or "")]
    if len(pages) <= max_tabs:
        return
    def score(tab: dict[str, Any]) -> tuple[int, int]:
        url = tab.get("url") or ""
        keep = 1 if keep_url_hint and keep_url_hint in url else 0
        user = 1 if "/user/" in url else 0
        return keep, user
    pages = sorted(pages, key=score, reverse=True)
    for tab in pages[max_tabs:]:
        tab_id = tab.get("id")
        if not tab_id:
            continue
        try:
            http_text(f"{cdp_url}/json/close/{parse.quote(tab_id, safe='')}")
            if log:
                log(f"closed extra Douyin tab: {tab.get('title', '')[:50]} {tab.get('url', '')[:120]}")
        except Exception as exc:
            if log:
                log(f"failed closing tab {tab_id}: {exc}")


def resolve_profile_url(page: CdpPage, url: str, timeout: float = 25) -> str:
    page.navigate(url, wait_seconds=3)
    deadline = time.time() + timeout
    last = page.current_url()
    while time.time() < deadline:
        current = page.current_url()
        if current:
            last = current
        if current and "v.douyin.com" not in current:
            time.sleep(2)
            return page.current_url() or current
        time.sleep(0.5)
    return last


def get_creator_name(page: CdpPage) -> str:
    script = r"""
(() => {
  const meta = document.querySelector('meta[name="keywords"],meta[property="og:title"],meta[name="description"]');
  const candidates = [
    document.querySelector('h1')?.innerText,
    document.querySelector('[data-e2e="user-title"]')?.innerText,
    document.querySelector('[class*="user"] h2')?.innerText,
    meta?.content,
    document.title
  ].filter(Boolean).map(v => String(v).replace(/\s+/g, ' ').trim());
  return candidates[0] || '';
})()
"""
    name = clean_text(page.eval(script), 120)
    name = re.sub(r"[-_｜|].*$", "", name).strip()
    return name


def collect_profile_videos(
    page: CdpPage,
    limit: int,
    log,
    target_video_id: str = "",
    humanize: bool = False,
    min_delay: float = 2.0,
    max_delay: float = 6.0,
) -> list[VideoCandidate]:
    seen: dict[str, VideoCandidate] = {}
    stable_rounds = 0
    max_rounds = 260 if limit <= 0 else 80
    for round_no in range(max_rounds):
        for item in get_video_candidates_from_dom(page):
            key = item.video_id or item.video_url
            if key and key not in seen:
                seen[key] = item
        log(f"profile scan round={round_no + 1} videos={len(seen)}")
        if target_video_id and target_video_id in seen:
            return [seen[target_video_id]]
        if limit > 0 and len(seen) >= limit:
            break
        before = len(seen)
        if humanize and random.random() < 0.28:
            result = scroll_profile_container(page, -(0.75 + random.random() * 0.35))
            log(f"profile reverse page scroll result={result}")
            human_pause(True, min_delay, max_delay, log, "profile reverse page scroll")
        result = scroll_profile_container(page, 0.9 + random.random() * 0.35)
        log(f"profile forward page scroll result={result}")
        if humanize:
            human_pause(True, min_delay, max_delay, log, "profile scan")
        else:
            time.sleep(1.5)
        payloads = page.drain_json_payloads(max_items=60)
        for item in get_video_candidates_from_payloads(payloads):
            key = item.video_id or item.video_url
            if key and key not in seen:
                seen[key] = item
        if len(seen) == before:
            stable_rounds += 1
        else:
            stable_rounds = 0
        stable_limit = 12 if limit <= 0 else 8
        if stable_rounds >= stable_limit:
            break
    if target_video_id:
        return []
    values = list(seen.values())
    return values if limit <= 0 else values[:limit]


def get_video_candidates_from_dom(page: CdpPage) -> list[VideoCandidate]:
    script = r"""
(() => {
  const out = [];
  const anchors = Array.from(document.querySelectorAll('a[href]'));
  for (const a of anchors) {
    const href = new URL(a.getAttribute('href'), location.href).href;
    const text = [a.innerText, a.getAttribute('title'), a.getAttribute('aria-label')]
      .filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
    const rect = a.getBoundingClientRect();
    const visible = rect.width > 20 && rect.height > 20;
    if (!visible) continue;
    if (href.includes('/video/') || href.includes('modal_id=') || href.includes('/note/')) {
      out.push({href, text});
    }
  }
  return out;
})()
"""
    rows = page.eval(script) or []
    items: list[VideoCandidate] = []
    for row in rows:
        url = row.get("href", "")
        title = clean_text(row.get("text", ""))
        video_id = find_video_id(url, title)
        if not video_id and "/note/" in url:
            video_id = find_video_id(url.replace("/note/", "/video/"), title)
        if url:
            items.append(VideoCandidate(video_id=video_id, video_url=url, title_hint=title))
    return items


def get_video_candidates_from_payloads(payloads: list[tuple[str, Any]]) -> list[VideoCandidate]:
    items: list[VideoCandidate] = []
    for url, payload in payloads:
        if "/aweme/v1/web/aweme/post/" not in url:
            continue
        aweme_list = payload.get("aweme_list") if isinstance(payload, dict) else None
        if not isinstance(aweme_list, list):
            continue
        for obj in aweme_list:
            if not isinstance(obj, dict):
                continue
            aweme_id = first_string(obj, ("aweme_id", "item_id", "video_id", "group_id"))
            if not aweme_id or not re.fullmatch(r"\d{8,}", aweme_id):
                continue
            title = first_string(obj, ("desc", "title", "caption", "share_title"))
            video_url = f"https://www.douyin.com/video/{aweme_id}"
            items.append(VideoCandidate(video_id=aweme_id, video_url=video_url, title_hint=title))
    return items


def scroll_profile_container(page: CdpPage, screens: float) -> Any:
    return page.eval(
        f"""
(() => {{
  const candidates = Array.from(document.querySelectorAll('*')).filter(el => {{
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return r.width > 300 && r.height > 300 && (el.scrollHeight > el.clientHeight + 80 || ['auto','scroll'].includes(s.overflowY));
  }});
  const container = document.querySelector('.route-scroll-container') ||
    candidates.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight))[0] ||
    document.scrollingElement || document.documentElement;
  const amount = Math.floor((container.clientHeight || window.innerHeight) * {screens:.3f});
  container.scrollBy(0, amount);
  return {{
    tag: container.tagName,
    cls: String(container.className || '').slice(0, 100),
    scrollTop: container.scrollTop,
    scrollHeight: container.scrollHeight,
    clientHeight: container.clientHeight,
    amount
  }};
}})()
"""
    )


def human_profile_idle(page: CdpPage, enabled: bool, min_delay: float, max_delay: float, log) -> None:
    if not enabled:
        return
    try:
        action_count = random.randint(1, 3)
        for idx in range(action_count):
            direction = -1 if random.random() < 0.35 else 1
            factor = random.uniform(0.8, 1.2)
            result = scroll_profile_container(page, direction * factor)
            log(f"profile idle scroll {idx + 1}/{action_count}: {result}")
            human_pause(True, min_delay, max_delay, log, f"profile idle scroll {idx + 1}/{action_count}")
        if random.random() < 0.45:
            human_pause(True, min_delay, max_delay, log, "profile idle reading")
    except Exception as exc:
        log(f"humanize profile idle skipped: {exc}")


def walk_json(value: Any):
    value = parse_embedded_json(value)
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def walk_json_with_related(value: Any, video_id: str, inherited_related: bool = False):
    value = parse_embedded_json(value)
    if isinstance(value, dict):
        object_text = json.dumps(value, ensure_ascii=False)[:4000]
        object_video_id = first_string(value, ("aweme_id", "item_id", "video_id", "group_id", "id"))
        is_related = inherited_related or not video_id or video_id in object_text or object_video_id == video_id
        yield value, is_related
        for child in value.values():
            yield from walk_json_with_related(child, video_id, is_related)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json_with_related(child, video_id, inherited_related)


def first_string(obj: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return clean_text(value, 500)
        if isinstance(value, (int, float)) and value:
            return str(value)
    return ""


def valid_product_id(value: str) -> str:
    value = clean_text(value, 80)
    return value if re.fullmatch(r"\d{8,}", value) else ""


def parse_time_value(value: Any) -> str:
    if value in ("", None):
        return ""
    try:
        num = int(value)
    except Exception:
        return clean_text(value, 80)
    if num > 10_000_000_000:
        num = int(num / 1000)
    if num > 1_000_000_000:
        return datetime.fromtimestamp(num).strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def extract_metadata_from_json(video_id: str, payloads: list[tuple[str, Any]]) -> tuple[str, str, list[ProductInfo]]:
    title = ""
    publish_time = ""
    products: list[ProductInfo] = []
    product_seen: set[tuple[str, str, str]] = set()

    for url, payload in payloads:
        for obj, is_related in walk_json_with_related(payload, video_id):
            object_text = json.dumps(obj, ensure_ascii=False)[:4000]
            object_video_id = first_string(obj, ("aweme_id", "item_id", "video_id", "group_id", "id"))

            if is_related and not title:
                title = first_string(obj, ("desc", "title", "caption", "share_title"))
            if is_related and not publish_time:
                for key in ("create_time", "publish_time", "createTime", "publishTime"):
                    if key in obj:
                        publish_time = parse_time_value(obj.get(key))
                        break

            if video_id and not is_related:
                continue
            product_keys = PRODUCT_ID_KEYS
            has_product_key = any(key in obj for key in product_keys)
            name = first_string(obj, PRODUCT_NAME_KEYS)
            if not name and has_product_key:
                name = first_string(obj, ("title", "name"))
            pid = valid_product_id(first_string(obj, product_keys))
            product_url = first_string(obj, PRODUCT_URL_KEYS)
            if not pid and product_url:
                pid = find_product_id(product_url, object_text)
            is_product_url = "product" in url.lower() or "ecom" in url.lower() or "shop" in url.lower()
            if has_product_key or pid or (is_product_url and (name or product_url)):
                if name or pid or product_url:
                    key = (name, pid, product_url)
                    if key not in product_seen:
                        product_seen.add(key)
                        products.append(ProductInfo(product_name=name, product_id=pid, product_url=product_url))

    return title, publish_time, products


def click_product_card_and_extract(page: CdpPage) -> list[ProductInfo]:
    click_script = r"""
(() => {
  const nodes = Array.from(document.querySelectorAll('button,a,div,span'));
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 5 && r.height > 5 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const candidates = nodes.filter(el => visible(el) && /购物|购买|商品|商城/.test(el.innerText || ''));
  const el = candidates[0];
  if (!el) return false;
  el.click();
  return true;
})()
"""
    clicked = page.eval(click_script)
    if not clicked:
        return []
    time.sleep(3)
    payloads = page.drain_json_payloads(max_items=40)
    _, _, products = extract_metadata_from_json("", payloads)
    dom_products = extract_products_from_dom(page)
    products.extend(dom_products)
    return dedupe_products(products)


def extract_products_from_dom(page: CdpPage) -> list[ProductInfo]:
    script = r"""
(() => {
  const anchors = Array.from(document.querySelectorAll('a[href]')).map(a => ({
    href: new URL(a.getAttribute('href'), location.href).href,
    text: (a.innerText || a.getAttribute('title') || '').replace(/\s+/g, ' ').trim()
  }));
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 20 && r.height > 8 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const texts = Array.from(document.querySelectorAll('div,span,p,h1,h2,h3,a'))
    .filter(visible)
    .map(el => (el.innerText || '').replace(/\s+/g, ' ').trim())
    .filter(t => t.length >= 8 && t.length <= 140);
  const body = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
  return {anchors, texts: Array.from(new Set(texts)).slice(0, 120), body: body.slice(0, 5000)};
})()
"""
    data = page.eval(script) or {}
    products: list[ProductInfo] = []
    names: list[str] = []
    product_words = re.compile(r"(孕妇|裤|裙|衣|装|鞋|包|内衣|托腹|凉感|休闲|长裤|短裤|商品)")
    noise_words = re.compile(r"(首页|推荐|关注|评论|分享|搜索|发送|客服|进店|详情|评价|保障|物流|立即购买)")
    for text in data.get("texts", []):
        text = clean_text(text, 180)
        if product_words.search(text) and not noise_words.fullmatch(text):
            names.append(text)
    for a in data.get("anchors", []):
        href = a.get("href", "")
        text = clean_text(a.get("text", ""), 180)
        pid = find_product_id(href, text)
        if pid or any(word in href.lower() for word in ("product", "ecom", "shop", "goods")):
            products.append(ProductInfo(product_name=text or (names[0] if names else ""), product_id=pid, product_url=href))
    body = data.get("body", "")
    pid = find_product_id("", body)
    if pid:
        products.append(ProductInfo(product_name=names[0] if names else "", product_id=pid, product_url=""))
    if names and not products:
        products.append(ProductInfo(product_name=names[0], product_id="", product_url=""))
    return dedupe_products(products)


def dedupe_products(products: list[ProductInfo]) -> list[ProductInfo]:
    out: list[ProductInfo] = []
    seen: set[tuple[str, str, str]] = set()
    for p in products:
        if not (p.product_name or p.product_id or p.product_url):
            continue
        p.product_id = valid_product_id(p.product_id)
        if not is_valid_product(p):
            continue
        if p.product_id:
            duplicate_id_indexes = [idx for idx, item in enumerate(out) if item.product_id == p.product_id]
            if duplicate_id_indexes:
                existing = out[duplicate_id_indexes[0]]
                if not existing.product_name and p.product_name:
                    existing.product_name = p.product_name
                if not existing.product_url and p.product_url:
                    existing.product_url = p.product_url
                continue
        key = (p.product_name, p.product_id, p.product_url)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def product_matches_video_text(product: ProductInfo, title: str) -> bool:
    name = product.product_name or ""
    if not name:
        return True
    title = title or ""
    keywords = (
        "孕妇",
        "孕期",
        "孕妈",
        "裤",
        "短裤",
        "阔腿裤",
        "裙",
        "半身裙",
        "孕妇装",
        "托腹",
        "冰丝",
        "凉感",
        "休闲",
    )
    return any(word in title and word in name for word in keywords)


def title_suggests_commerce(title: str) -> bool:
    return bool(
        re.search(
            r"(买|入|价格|质量|舒服|好穿|孕妇裤|孕妇裙|孕妇装|短裤|阔腿裤|半身裙|托腹|冰丝|凉感|休闲裤|外穿)",
            title or "",
        )
    )


def collect_video_detail(
    page: CdpPage,
    video: VideoCandidate,
    creator_name: str,
    profile_url: str,
    source_url: str,
    evidence_dir: Path,
    humanize: bool = False,
    min_delay: float = 2.0,
    max_delay: float = 6.0,
    log=None,
) -> list[dict[str, Any]]:
    collect_time = now_text()
    try:
        page.finished_requests.clear()
        human_pause(humanize, min_delay, max_delay, log, "before opening video")
        page.navigate(video.video_url, wait_seconds=2 if humanize else 5)
        human_pause(humanize, min_delay, min(max_delay, 5.0), log, "video reading")
        if not humanize:
            time.sleep(2)
        payloads = page.drain_json_payloads(max_items=80)
        title, publish_time, products = extract_metadata_from_json(video.video_id, payloads)
        if not title:
            title = get_dom_video_title(page) or video.title_hint
        if not products or not any(p.product_name for p in products):
            clicked_products = click_product_card_and_extract(page)
            clicked_products = [p for p in clicked_products if product_matches_video_text(p, title or video.title_hint)]
            if clicked_products:
                products = dedupe_products(clicked_products + products)
        products = dedupe_products(products)

        base = {
            "creator_name": creator_name,
            "creator_profile_url": profile_url,
            "source_profile_url": source_url,
            "video_id": video.video_id or find_video_id(page.current_url(), title),
            "video_url": video.video_url,
            "video_title": clean_text(title, 500),
            "publish_time": publish_time,
            "collect_time": collect_time,
            "collect_status": "ok",
            "error_message": "",
        }
        if not products:
            if page_has_login_prompt(page):
                base["collect_status"] = "partial_login_required_for_product"
                base["error_message"] = "Chrome profile is not logged in or product card is hidden; product fields are unknown."
                return [{**base, "has_product": "", "product_name": "", "product_id": "", "product_url": ""}]
            if title_suggests_commerce(base["video_title"]):
                base["collect_status"] = "partial_product_not_exposed"
                base["error_message"] = "Video text looks commerce-related, but no valid product id was exposed after network and card extraction."
                return [{**base, "has_product": "", "product_name": "", "product_id": "", "product_url": ""}]
            base["collect_status"] = "ok_no_product_detected"
            return [{**base, "has_product": False, "product_name": "", "product_id": "", "product_url": ""}]
        return [
            {
                **base,
                "has_product": True,
                "product_name": p.product_name,
                "product_id": p.product_id,
                "product_url": p.product_url,
            }
            for p in products
        ]
    except Exception as exc:
        shot = evidence_dir / f"failed_{video.video_id or int(time.time())}.png"
        page.screenshot(shot)
        return [
            {
                "creator_name": creator_name,
                "creator_profile_url": profile_url,
                "source_profile_url": source_url,
                "video_id": video.video_id,
                "video_url": video.video_url,
                "video_title": video.title_hint,
                "publish_time": "",
                "has_product": "",
                "product_name": "",
                "product_id": "",
                "product_url": "",
                "collect_time": collect_time,
                "collect_status": "failed",
                "error_message": f"{type(exc).__name__}: {exc}; screenshot={shot}",
            }
        ]


def get_dom_video_title(page: CdpPage) -> str:
    script = r"""
(() => {
  const meta = document.querySelector('meta[property="og:title"],meta[name="description"]');
  const candidates = [
    document.querySelector('[data-e2e="video-desc"]')?.innerText,
    document.querySelector('h1')?.innerText,
    meta?.content,
    document.title
  ].filter(Boolean);
  return candidates.map(v => String(v).replace(/\s+/g, ' ').trim())[0] || '';
})()
"""
    return clean_text(page.eval(script), 500)


def page_has_login_prompt(page: CdpPage) -> bool:
    script = r"""
(() => {
  const texts = Array.from(document.querySelectorAll('button,a,div,span'))
    .map(el => (el.innerText || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean);
  return texts.some(t => t === '登录' || t === '立即登录' || t.includes('登录后'));
})()
"""
    try:
        return bool(page.eval(script))
    except Exception:
        return False


def write_excel(rows: list[dict[str, Any]], out_path: Path) -> None:
    ensure_dir(out_path.parent)
    wb = Workbook()
    ws = wb.active
    ws.title = "douyin_creator_tracker"
    ws.append(HEADERS)
    for row in rows:
        ws.append([row.get(h, "") for h in HEADERS])
    for cell in ws[1]:
        cell.style = "Headline 3"
    ws.freeze_panes = "A2"
    widths = {
        "A": 18,
        "B": 42,
        "C": 42,
        "D": 24,
        "E": 48,
        "F": 44,
        "G": 20,
        "H": 12,
        "I": 38,
        "J": 24,
        "K": 48,
        "L": 20,
        "M": 16,
        "N": 42,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    wb.save(out_path)


def rows_from_har(har_path: Path, video_id: str, source_url: str) -> list[dict[str, Any]]:
    payloads = load_har_payloads(har_path)
    title, publish_time, products = extract_metadata_from_json(video_id, payloads)
    collect_time = now_text()
    base = {
        "creator_name": "",
        "creator_profile_url": "",
        "source_profile_url": source_url or str(har_path),
        "video_id": video_id,
        "video_url": f"https://www.douyin.com/video/{video_id}" if video_id else "",
        "video_title": title,
        "publish_time": publish_time,
        "collect_time": collect_time,
        "collect_status": "ok" if products else "partial_no_product_in_har",
        "error_message": "" if products else "HAR parsed, but no product id/name/url was found in matched Douyin responses.",
    }
    if not products:
        return [{**base, "has_product": "", "product_name": "", "product_id": "", "product_url": ""}]
    return [
        {
            **base,
            "has_product": True,
            "product_name": p.product_name,
            "product_id": p.product_id,
            "product_url": p.product_url,
        }
        for p in products
    ]


def load_profile_urls(profile_url: str, profile_list: Path | None) -> list[str]:
    urls: list[str] = []
    if profile_list:
        for line in profile_list.read_text(encoding="utf-8", errors="replace").splitlines():
            value = line.strip().lstrip("\ufeff")
            if not value or value.startswith("#"):
                continue
            urls.append(value)
    if profile_url:
        urls.insert(0, profile_url)
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def load_incremental_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"videos": {}, "profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("videos", {})
            data.setdefault("profiles", {})
            return data
    except Exception:
        pass
    return {"videos": {}, "profiles": {}}


def save_incremental_index(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_rows_in_index(index: dict[str, Any], profile_url: str, rows: list[dict[str, Any]]) -> None:
    profile_bucket = index.setdefault("profiles", {}).setdefault(profile_url, {"video_ids": []})
    profile_ids = set(profile_bucket.get("video_ids") or [])
    videos = index.setdefault("videos", {})
    for row in rows:
        video_id = str(row.get("video_id") or "")
        if not video_id:
            continue
        profile_ids.add(video_id)
        videos[video_id] = {
            "profile_url": profile_url,
            "video_url": row.get("video_url", ""),
            "video_title": row.get("video_title", ""),
            "product_id": row.get("product_id", ""),
            "collect_status": row.get("collect_status", ""),
            "collect_time": row.get("collect_time", ""),
        }
    profile_bucket["video_ids"] = sorted(profile_ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track Douyin creator video commerce data through Chrome CDP.")
    parser.add_argument("--profile-url", default="", help=f"Douyin creator profile URL or short URL, default {DEFAULT_PROFILE_URL} when --profile-list is not provided")
    parser.add_argument("--profile-list", type=Path, help="Text file with one creator profile URL per line")
    parser.add_argument("--video-id", default="", help="Optional target video id, used by --har parsing")
    parser.add_argument("--target-video-id", default="", help="Only collect this video id from the creator profile")
    parser.add_argument("--har", type=Path, help="Parse a Chrome DevTools HAR export instead of connecting to CDP")
    parser.add_argument("--limit", type=int, default=5, help="Number of videos to collect")
    parser.add_argument("--all", action="store_true", help="Collect all discoverable videos from the creator profile")
    parser.add_argument("--humanize", action="store_true", help="Add random pauses and harmless profile scrolls between actions")
    parser.add_argument("--min-delay", type=float, default=3.0, help="Minimum random delay seconds when --humanize is enabled")
    parser.add_argument("--max-delay", type=float, default=9.0, help="Maximum random delay seconds when --humanize is enabled")
    parser.add_argument("--retries", type=int, default=1, help="Retry count for a failed video after reconnecting CDP")
    parser.add_argument("--incremental", action="store_true", help="Skip videos already recorded in the incremental index")
    parser.add_argument("--incremental-db", type=Path, default=DEFAULT_INCREMENTAL_DB, help="Incremental index JSON path")
    parser.add_argument("--close-extra-tabs", action="store_true", help="Close extra Douyin tabs before/after each creator run")
    parser.add_argument("--max-tabs", type=int, default=3, help="Maximum Douyin tabs to keep when --close-extra-tabs is enabled")
    parser.add_argument("--no-keep-awake", action="store_true", help="Do not request Windows to stay awake during collection")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output .xlsx path")
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Chrome CDP URL, default http://127.0.0.1:9222")
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR, help="Log/screenshot directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dir(args.evidence_dir)
    log_path = args.evidence_dir / "run.log"
    log_path.write_text(f"[{now_text()}] start\n", encoding="utf-8")

    def log(message: str) -> None:
        print(message, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{now_text()}] {message}\n")

    rows: list[dict[str, Any]] = []
    page: CdpPage | None = None
    keep_awake_stop: threading.Event | None = None
    try:
        keep_awake_stop = start_keep_awake_thread(not args.no_keep_awake, log)
        if args.har:
            log(f"parsing HAR: {args.har}")
            rows = rows_from_har(args.har, args.video_id, args.profile_url)
            write_excel(rows, args.out)
            log(f"wrote Excel: {args.out.resolve()}")
            log(f"done rows={len(rows)}")
            return 0

        if not args.profile_url and not args.profile_list:
            args.profile_url = DEFAULT_PROFILE_URL
        profile_urls = load_profile_urls(args.profile_url, args.profile_list)
        if not profile_urls:
            raise CdpError("No creator profile URL provided")
        incremental_index = load_incremental_index(args.incremental_db) if args.incremental else {"videos": {}, "profiles": {}}
        skipped_existing = set(incremental_index.get("videos", {}).keys()) if args.incremental else set()

        log(f"connecting Chrome CDP: {args.cdp_url}")
        for profile_no, source_profile_url in enumerate(profile_urls, start=1):
            if args.close_extra_tabs:
                close_extra_douyin_tabs(args.cdp_url, source_profile_url, args.max_tabs, log)
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            page = connect_or_create_tab(args.cdp_url, source_profile_url, log_path)
            log(f"opening profile {profile_no}/{len(profile_urls)}: {source_profile_url}")
            final_profile_url = resolve_profile_url(page, source_profile_url)
            if not final_profile_url:
                raise CdpError("profile URL resolution returned empty URL")
            if "captcha" in final_profile_url.lower():
                raise CdpError(f"captcha page detected: {final_profile_url}")
            log(f"resolved profile URL: {final_profile_url}")
            creator_name = get_creator_name(page)
            log(f"creator name: {creator_name or '(unknown)'}")

            requested_limit = 0 if args.all else args.limit
            videos = collect_profile_videos(
                page,
                requested_limit,
                log,
                args.target_video_id,
                args.humanize,
                args.min_delay,
                args.max_delay,
            )
            if args.incremental:
                before_count = len(videos)
                videos = [v for v in videos if (v.video_id or find_video_id(v.video_url, v.title_hint)) not in skipped_existing]
                log(f"incremental skipped existing videos: {before_count - len(videos)}")
            if not videos:
                if args.target_video_id:
                    raise CdpError(f"Target video card not found or already collected: {args.target_video_id}")
                log("no new video cards found for this profile")
                continue
            log(f"collected video cards: {len(videos)}")

            for idx, video in enumerate(videos, start=1):
                log(f"collecting profile {profile_no}/{len(profile_urls)} video {idx}/{len(videos)}: {video.video_id or video.video_url}")
                if idx > 1:
                    try:
                        page.navigate(final_profile_url, wait_seconds=2)
                        human_profile_idle(page, args.humanize, args.min_delay, args.max_delay, log)
                    except Exception as exc:
                        log(f"profile idle before video skipped: {exc}")
                attempt = 0
                while True:
                    video_rows = collect_video_detail(
                        page=page,
                        video=video,
                        creator_name=creator_name,
                        profile_url=final_profile_url,
                        source_url=source_profile_url,
                        evidence_dir=args.evidence_dir,
                        humanize=args.humanize,
                        min_delay=args.min_delay,
                        max_delay=args.max_delay,
                        log=log,
                    )
                    failed = video_rows and video_rows[0].get("collect_status") == "failed"
                    error_message = video_rows[0].get("error_message", "") if video_rows else ""
                    retryable = "CDP timeout" in error_message or "CdpError" in error_message
                    if not failed or not retryable or attempt >= args.retries:
                        break
                    attempt += 1
                    log(f"retrying video after CDP reconnect attempt={attempt}: {video.video_id or video.video_url}")
                    try:
                        page.close()
                    except Exception:
                        pass
                    page = connect_or_create_tab(args.cdp_url, final_profile_url, log_path)
                    page.navigate(final_profile_url, wait_seconds=2)
                rows.extend(video_rows)
                if args.incremental:
                    mark_rows_in_index(incremental_index, final_profile_url, video_rows)
                    save_incremental_index(args.incremental_db, incremental_index)
                    skipped_existing.update(str(r.get("video_id") or "") for r in video_rows if r.get("video_id"))
                log(f"video {idx} rows={len(video_rows)} status={video_rows[0].get('collect_status')}")
                write_excel(rows, args.out)
                log(f"checkpoint wrote Excel rows={len(rows)}: {args.out.resolve()}")
            if args.close_extra_tabs:
                close_extra_douyin_tabs(args.cdp_url, final_profile_url, args.max_tabs, log)

        write_excel(rows, args.out)
        log(f"wrote Excel: {args.out.resolve()}")
        log(f"done rows={len(rows)}")
        return 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(error, file=sys.stderr)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{now_text()}] ERROR {error}\n")
            f.write(traceback.format_exc())
        if rows:
            write_excel(rows, args.out)
        return 1
    finally:
        if keep_awake_stop:
            keep_awake_stop.set()
            clear_keep_awake(log)
        if page:
            page.close()


if __name__ == "__main__":
    raise SystemExit(main())
