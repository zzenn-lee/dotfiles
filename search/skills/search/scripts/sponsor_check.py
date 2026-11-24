"""Sponsor (협찬) detection core for Naver mobile blog posts.

Pure stdlib (html.parser, re). No network access, no third-party deps.
This module only parses already-fetched HTML and decides a verdict; task 2
layers URL handling / fetching / CLI on top of the functions below.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Constants (verbatim per task brief)
# ---------------------------------------------------------------------------

STRONG_PHRASES = [
    "소정의 원고료",
    "원고료를 받",
    "제품을 제공받",
    "제공받아",
    "지원받아",
    "협찬을 받",
    "체험단",
    "유료광고",
    "유료 광고",
    "업체로부터",
    "#광고",
    "#협찬",
    "광고 포함",
]

WEAK_PATTERNS = [
    r"0\d{1,2}-\d{3,4}-\d{4}",  # phone number, same one repeated >= 2 times
    "쿠폰코드",
    "할인코드",
    "광고",  # bare, only counted near the very start/end of the post
]

REVIEW_DOMAINS = [
    "revu.net",
    "reviewnote.co.kr",
    "mrblog.net",
    "dinnerqueen.net",
    "reviewplace.co.kr",
    "ringble.co.kr",
    "seoulouba.co.kr",
    "storyn.kr",
    "tble.kr",
    "cometoplay.kr",
    "popomon.com",
    "assaview.co.kr",
]

NEGATIONS = [
    "아님",
    "아닙니다",
    "아니에요",
    "없이",
    "0원 협찬 아님",
]

PROS_CONS_WORDS = [
    "장점",
    "단점",
    "아쉬",
    "별로",
    "불편",
    "비추",
    "좋았",
    "만족",
    "재방문",
    "추천",
    "후회",
    "가성비",
]

_NAEDON = "내돈내산"
_NEGATION_WINDOW = 15
_BARE_GWANGGO_EDGE = 300

_ROOT_CLASSES = ("se-main-container",)
_ROOT_FALLBACK_IDS = ("viewTypeSelector",)
_ROOT_FALLBACK_CLASSES = ("post_ct",)
_TITLE_CLASS = "se-title-text"
_DATE_CLASSES = ("blog_date", "se_publishDate")
_VOID_TAGS = {"br", "img", "meta", "link", "hr", "input", "area", "base", "col", "embed", "source", "track", "wbr"}
# Block-level boundaries that start a fresh paragraph: se-editor component
# wrappers are plain <div>s, and old-editor/minified markup relies on bare
# <p>/<div>/list/heading/blockquote tags instead of literal newlines.
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}
_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# parse_post
# ---------------------------------------------------------------------------


class _PostParser(HTMLParser):
    """Minimal stdlib HTML parser for Naver mobile blog post markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.og_title = ""
        self._title_chunks: list[str] = []
        self._date_chunks: list[str] = []
        self.links: list[str] = []
        self.images: list[str] = []
        self.paragraphs: list[str] = []

        self._buf: list[str] = []
        self._stack: list[str] = []
        self._root_open_idx: int | None = None
        self._title_open_idx: int | None = None
        self._date_open_idx: int | None = None

    # -- helpers -----------------------------------------------------
    def _flush_para(self) -> None:
        text = _WHITESPACE_RE.sub(" ", "".join(self._buf)).strip()
        self._buf = []
        if text:
            self.paragraphs.append(text)

    # -- HTMLParser hooks ---------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        classes = (d.get("class") or "").split()
        tag_id = d.get("id") or ""

        if tag == "meta" and d.get("property") == "og:title":
            self.og_title = d.get("content") or ""

        in_root = self._root_open_idx is not None
        opening_root_now = False
        if not in_root and (
            any(c in classes for c in _ROOT_CLASSES)
            or tag_id in _ROOT_FALLBACK_IDS
            or any(c in classes for c in _ROOT_FALLBACK_CLASSES)
        ):
            in_root = True
            opening_root_now = True

        if in_root and tag == "a":
            href = d.get("href")
            if href:
                self.links.append(href)
        if in_root and tag == "img":
            url = d.get("data-lazy-src") or d.get("src")
            if url:
                self.images.append(url)

        opening_title = _TITLE_CLASS in classes
        opening_date = any(c in classes for c in _DATE_CLASSES)

        # paragraph boundaries: a new block-level element (se-component,
        # bare <p>/<div>, list items, headings, blockquotes) or <br> starts
        # a fresh chunk — covers both the new se-editor and minified
        # old-editor markup with no literal newlines between tags.
        if in_root and not opening_root_now and tag in _BLOCK_TAGS:
            self._flush_para()
        if in_root and tag == "br":
            self._flush_para()

        if tag not in _VOID_TAGS:
            self._stack.append(tag)
            idx = len(self._stack) - 1
            if opening_root_now:
                self._root_open_idx = idx
            if opening_title:
                self._title_open_idx = idx
            if opening_date:
                self._date_open_idx = idx

    def handle_endtag(self, tag: str) -> None:
        if tag not in self._stack:
            return  # void / stray close tag we never pushed — ignore
        # Implicit close: pop everything above and including the matching
        # open tag, so an unclosed non-void tag (e.g. a stray <span>) can't
        # permanently desync root/title/date tracking for the rest of the
        # document.
        while self._stack:
            idx = len(self._stack) - 1
            popped = self._stack.pop()
            if self._root_open_idx is not None and idx == self._root_open_idx:
                self._flush_para()
                self._root_open_idx = None
            if self._title_open_idx is not None and idx == self._title_open_idx:
                self._title_open_idx = None
            if self._date_open_idx is not None and idx == self._date_open_idx:
                self._date_open_idx = None
            if popped == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._title_open_idx is not None:
            self._title_chunks.append(data)
        if self._date_open_idx is not None:
            self._date_chunks.append(data)
        if self._root_open_idx is not None:
            self._buf.append(data)

    def close(self) -> None:
        super().close()
        self._flush_para()

    @property
    def title_text(self) -> str:
        return "".join(self._title_chunks).strip()

    @property
    def date_text(self) -> str:
        return "".join(self._date_chunks).strip()


def parse_post(html: str) -> dict:
    """Extract title/date/text/links/images from a Naver mobile blog post page."""
    parser = _PostParser()
    parser.feed(html)
    parser.close()

    title = parser.title_text or parser.og_title
    text = "\n".join(parser.paragraphs)

    return {
        "title": title,
        "date": parser.date_text,
        "text": text,
        "links": parser.links,
        "images": parser.images,
    }


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------


def _position(idx: int, length: int) -> str:
    if length <= 0:
        return "중간"
    ratio = idx / length
    if ratio < 0.15:
        return "맨 위"
    if ratio > 0.85:
        return "맨 아래"
    return "중간"


def _find_all(text: str, needle: str) -> list[int]:
    idxs = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx == -1:
            break
        idxs.append(idx)
        start = idx + max(len(needle), 1)
    return idxs


def _is_negated(text: str, idx: int, phrase_len: int) -> bool:
    window_start = max(0, idx - _NEGATION_WINDOW)
    window_end = min(len(text), idx + phrase_len + _NEGATION_WINDOW)
    window = text[window_start:window_end]
    return any(neg in window for neg in NEGATIONS)


def detect(post: dict) -> tuple[str, list[dict]]:
    """Decide 협찬/의심/없음 for a parsed post, with supporting evidence."""
    text = post.get("text") or ""
    links = post.get("links") or []
    images = post.get("images") or []
    n = len(text)

    strong_hits: list[dict] = []  # evidence items, excluding the 내돈내산 add-on

    for phrase in STRONG_PHRASES:
        for idx in _find_all(text, phrase):
            if _is_negated(text, idx, len(phrase)):
                continue
            strong_hits.append({"signal": phrase, "position": _position(idx, n)})

    url_pool = list(links) + list(images)
    for domain in REVIEW_DOMAINS:
        if any(domain in url for url in url_pool):
            strong_hits.append({"signal": domain, "position": "링크/이미지"})

    if strong_hits:
        evidence = list(strong_hits)
        if _NAEDON in text:
            naedon_idx = text.find(_NAEDON)
            evidence.append(
                {
                    "signal": "내돈내산 표기와 협찬 표시가 함께 있음",
                    "position": _position(naedon_idx, n),
                }
            )
        return "협찬", evidence

    weak_evidence: list[dict] = []

    phone_hits: dict[str, list[int]] = {}
    for m in re.finditer(r"0\d{1,2}-\d{3,4}-\d{4}", text):
        phone_hits.setdefault(m.group(), []).append(m.start())
    for phone, idxs in phone_hits.items():
        if len(idxs) >= 2:
            weak_evidence.append(
                {"signal": f"같은 전화번호({phone}) 반복 등장", "position": _position(idxs[0], n)}
            )

    for kw in ("쿠폰코드", "할인코드"):
        idx = text.find(kw)
        if idx != -1:
            weak_evidence.append({"signal": kw, "position": _position(idx, n)})

    for idx in _find_all(text, "광고"):
        if idx < _BARE_GWANGGO_EDGE or idx >= n - _BARE_GWANGGO_EDGE:
            weak_evidence.append({"signal": "광고", "position": _position(idx, n)})
            break

    if weak_evidence:
        return "의심", weak_evidence
    return "없음", []


# ---------------------------------------------------------------------------
# excerpt
# ---------------------------------------------------------------------------


def excerpt(text: str, limit: int = 3000) -> str:
    """Head + tail + every pros/cons-bearing paragraph, deduped, in order."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    n = len(text)
    segments: list[tuple[int, str]] = [(0, text[:600])]
    if n > 600:
        tail_start = max(n - 600, 600)
        segments.append((tail_start, text[tail_start:]))

    offset = 0
    for para in text.split("\n"):
        if any(word in para for word in PROS_CONS_WORDS):
            start = text.find(para, offset)
            if start == -1:
                start = offset
            segments.append((start, para))
        offset += len(para) + 1  # account for the "\n" separator

    segments.sort(key=lambda item: item[0])

    seen: set[str] = set()
    pieces: list[str] = []
    for _, content in segments:
        if not content or content in seen:
            continue
        seen.add(content)
        pieces.append(content)

    return "\n".join(pieces)[:limit]
