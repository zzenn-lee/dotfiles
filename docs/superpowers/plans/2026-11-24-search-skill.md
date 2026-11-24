# /search Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/search` Claude Code skill that proposes a topic-shaped report plan, gathers sources with the installed tools, flags sponsored Naver blog posts with a deterministic script, and publishes a judgment-ready report as a claude.ai Artifact (+ md copy).

**Architecture:** `SKILL.md` carries the judgment work (plan proposal, source choice, pros/cons extraction, cross-check, report). One stdlib-only Python script, `sponsor_check.py`, turns Naver blog URLs into `{verdict, evidence, excerpt}` JSON so sponsorship is judged the same way every time. `install-mac.sh` symlinks the skill folder into `~/.claude/skills/search`.

**Tech Stack:** Python 3.11+ stdlib only (`html.parser`, `urllib`, `json`, `unittest`), Markdown skill file, bash.

**Spec:** `docs/superpowers/specs/2026-11-24-search-skill-design.md`

## Global Constraints

- Mac only, Claude Code only (SSH/remote included). Plan confirmation in chat; result = claude.ai Artifact link.
- No paid tools. Budgets per run: SerpAPI ≤ 10 calls, ScrapeCreators ≤ 100 credits, blog sponsor checks ≤ 30 posts; exceeding any needs the user's OK at plan time.
- General web search → WebSearch first. SerpAPI only for Korean-localized Google, Google Shopping/Hotels/Flights/Maps, `site:` searches of Korean communities.
- Instagram not used. Naver cafe posts: preview only, never read in full, never sponsor-checked.
- Sponsored posts are labeled, never dropped.
- dotfiles is a PUBLIC repo: no real third-party blog text in fixtures; never print or commit API keys.
- Source tiers exactly: `A 공식`, `B 실사용`, `C 정리글`, `D 협찬·광고`.
- Script verdict values exactly: `협찬`, `의심`, `없음`, `읽기실패`.

## Review Focus

1. A post that says "협찬 아닙니다" / "내돈내산" only → must be `없음`, not `협찬` (Task 1 test `test_negated_disclosure_is_not_sponsored`).
2. "광고" used in an ordinary sentence mid-post ("광고에서 보던 그 맛") → not flagged (Task 1 `test_plain_word_gwanggo_mid_text_not_flagged`).
3. Disclosure only as a banner image linking to a 체험단 site, no text → `협찬` via domain (Task 1 `test_banner_image_domain_detected`).
4. A non-blog URL (cafe, other site) in the input → that item `읽기실패` with reason, others still processed (Task 2 `test_non_blog_url_reported_not_raised`).
5. One URL times out / 404 → `읽기실패`, run continues, exit code 0 (Task 2 `test_fetch_failure_continues`).

---

### Task 1: Sponsor detection core (offline)

**Files:**
- Create: `search/skills/search/scripts/sponsor_check.py`
- Create: `search/skills/search/tests/test_sponsor_check.py`
- Create: `search/skills/search/tests/fixtures/{sponsored_bottom,sponsored_top,banner_only,plain,negated,mixed_naedon}.html` (hand-written, structure mimics `m.blog.naver.com`: `meta[og:title]`, `.se-title-text`, `.blog_date`, `div.se-main-container` > `.se-component` paragraphs; old-editor variant `#viewTypeSelector` in `plain.html`)

**Interfaces:**
- Produces:
  - `parse_post(html: str) -> dict` → `{"title": str, "date": str, "text": str, "links": list[str], "images": list[str]}` (text = body paragraphs joined by `\n`; title from `.se-title-text` else `og:title`; date from `.blog_date`/`.se_publishDate`; body root `.se-main-container` else `#viewTypeSelector`/`.post_ct`)
  - `detect(post: dict) -> tuple[str, list[dict]]` → `(verdict, evidence)`; evidence item `{"signal": str, "position": "맨 위"|"중간"|"맨 아래"|"링크/이미지"}`
  - `excerpt(text: str, limit: int = 3000) -> str`
  - Constants `STRONG_PHRASES`, `WEAK_PATTERNS`, `REVIEW_DOMAINS`, `NEGATIONS`, `PROS_CONS_WORDS`

Rules `detect` must implement:
- Strong phrases (→ `협찬`): 소정의 원고료, 원고료를 받, 제품을 제공받, 제공받아, 지원받아, 협찬을 받, 체험단, 유료광고, 유료 광고, 업체로부터, #광고, #협찬, 광고 포함.
- A strong match within 15 chars of a negation (아님, 아닙니다, 아니에요, 없이, 0원 협찬 아님) is ignored.
- `REVIEW_DOMAINS` (strong, position `링크/이미지`): revu.net, reviewnote.co.kr, mrblog.net, dinnerqueen.net, reviewplace.co.kr, ringble.co.kr, seoulouba.co.kr, storyn.kr, tble.kr, cometoplay.kr, popomon.com, assaview.co.kr — matched in `links` or `images`.
- Weak (→ `의심` if no strong): same phone number (`0\d{1,2}-\d{3,4}-\d{4}`) ≥ 2 times; 쿠폰코드/할인코드; bare 광고 only within first or last 300 chars.
- 내돈내산 together with any strong signal → add evidence `{"signal": "내돈내산 표기와 협찬 표시가 함께 있음", ...}`.
- Position by match index / len(text): < 0.15 맨 위, > 0.85 맨 아래, else 중간.
- `excerpt`: first 600 chars + last 600 chars + every paragraph containing a `PROS_CONS_WORDS` item (장점, 단점, 아쉬, 별로, 불편, 비추, 좋았, 만족, 재방문, 추천, 후회, 가성비), de-duplicated, in original order, truncated to `limit`.

- [ ] **Step 1: Write fixtures and failing tests** — tests (unittest), one per behavior:
  - `test_parse_se_editor` — `sponsored_bottom.html` → title, date non-empty, text contains a known fixture sentence.
  - `test_parse_old_editor` — `plain.html` → text non-empty.
  - `test_sponsored_bottom` → verdict `협찬`, an evidence item position `맨 아래`.
  - `test_sponsored_top` → `협찬`, position `맨 위`.
  - `test_banner_image_domain_detected` — `banner_only.html` (only `<img src="https://revu.net/...">`) → `협찬`, position `링크/이미지`.
  - `test_plain_is_none` → `없음`, evidence `[]`.
  - `test_negated_disclosure_is_not_sponsored` — `negated.html` ("협찬 아닙니다, 내돈내산") → `없음`.
  - `test_plain_word_gwanggo_mid_text_not_flagged` — inline HTML with "광고에서 보던 그 맛" at the middle → `없음`.
  - `test_mixed_naedon_flags_both` — `mixed_naedon.html` → `협찬` and evidence contains "내돈내산 표기와 협찬 표시가 함께 있음".
  - `test_repeated_phone_is_suspect` — inline HTML with the same phone twice, no strong → `의심`.
  - `test_excerpt_keeps_tail_and_proscons` — 10,000-char text with "단점은 주차" in the middle and a unique last sentence → excerpt contains both, `len <= 3000`.

- [ ] **Step 2: Run, expect failures**
  Run: `cd search/skills/search && python3 -m unittest discover -s tests -v`
  Expected: errors — `sponsor_check` has no `parse_post`.

- [ ] **Step 3: Implement** `parse_post`, `detect`, `excerpt` and the constants in `sponsor_check.py` (stdlib `html.parser.HTMLParser` subclass that tracks being inside the body root and collects `a[href]`, `img[src|data-lazy-src]`).

- [ ] **Step 4: Run, expect pass** — same command, all tests OK.

- [ ] **Step 5: Commit** — `git add search/skills/search && git commit -m "feat(search): 협찬 판별 핵심 — 문구·체험단 도메인·위치 규칙, 장단점 발췌"`

### Task 2: URL handling, fetching, CLI

**Files:**
- Modify: `search/skills/search/scripts/sponsor_check.py`
- Modify: `search/skills/search/tests/test_sponsor_check.py`

**Interfaces:**
- Consumes: `parse_post`, `detect`, `excerpt` (Task 1).
- Produces:
  - `to_mobile_url(url: str) -> str | None` — accepts `blog.naver.com/{id}/{logNo}`, `m.blog.naver.com/{id}/{logNo}`, `…/PostView.naver?blogId=&logNo=` (http/https, with or without query noise) → `https://m.blog.naver.com/PostView.naver?blogId={id}&logNo={logNo}`; anything else → `None`.
  - `check(url: str, fetch=default_fetch) -> dict` → `{"url", "title", "date", "verdict", "evidence", "excerpt", "error"?}`; never raises. Non-blog → `verdict "읽기실패"`, `error "네이버 블로그 주소가 아님"`; fetch exception → `"읽기실패"`, `error` = short message.
  - `default_fetch(url: str) -> str` — `urllib.request` with an iPhone Safari User-Agent, 10 s timeout, follows redirects.
  - CLI: `python3 sponsor_check.py URL [URL ...]` or `--input FILE` (one URL per line or a JSON list) → prints a JSON array (UTF-8, `ensure_ascii=False`) of `check` results; `--max N` (default 30) keeps the first N; exit 0 unless arguments are invalid (exit 2).

- [ ] **Step 1: Failing tests**
  - `test_to_mobile_url_variants` — the three URL forms → identical PostView URL; `https://cafe.naver.com/x/1` → `None`.
  - `test_non_blog_url_reported_not_raised` — `check("https://cafe.naver.com/x/1")` → `읽기실패` with that error.
  - `test_fetch_failure_continues` — CLI-level function `run(urls, fetch)` (expose `run(urls: list[str], fetch=default_fetch, max_posts: int = 30) -> list[dict]`) with a fetch that raises for one URL and returns `sponsored_bottom.html` for another → 2 results, first `읽기실패`, second `협찬`.
  - `test_max_posts_cap` — 35 URLs, stub fetch → 30 results.
  - `test_cli_json_output` — `main(["--input", tmpfile], fetch=stub)` returns a JSON string; it parses to a list of 1 result and contains Korean as-is (no `\uXXXX`).

- [ ] **Step 2: Run, expect failures** (same command as Task 1).
- [ ] **Step 3: Implement** `to_mobile_url`, `default_fetch`, `check`, `run`, `main(argv: list[str], fetch=default_fetch) -> str`, `if __name__ == "__main__": print(main(sys.argv[1:]))`.
- [ ] **Step 4: Run, expect pass.**
- [ ] **Step 5: Live smoke (not committed)** — `python3 search/skills/search/scripts/sponsor_check.py <3 real blog URLs from a naver-search query, e.g. "성수 카페 체험단">` → valid JSON, at least one non-`읽기실패` result. Record the outcome in the task report only.
- [ ] **Step 6: Commit** — `feat(search): 블로그 주소 정규화·가져오기·CLI — 실패해도 나머지 계속`

### Task 3: SKILL.md, install link, docs

**Files:**
- Create: `search/skills/search/SKILL.md`
- Modify: `search/install-mac.sh` (link step), `search/README.md` (구성 표 + 파일 트리), root `README.md` (one line)

**Interfaces:**
- Consumes: CLI from Task 2 (`python3 ~/.claude/skills/search/scripts/sponsor_check.py --input FILE`).

SKILL.md must contain, in this order (English instructions, Korean output, like `claude/skills/explain/SKILL.md`):
1. Frontmatter: `name: search`; description "Use when the user asks to research/look up/compare/collect information for daily life — travel, shopping, products, venues, services, reviews, events — e.g. "/search", "알아봐줘", "찾아봐줘", "후기 모아줘", "정리해줘(검색)", "비교해줘"."
2. Step 1 Plan (stop and wait): topic type → body template (spec §7 table), sources to use with reason, expected usage, current balances. Balance commands read keys from `~/.config/search/keys.env` without echoing them: SerpAPI `https://serpapi.com/account.json` → `total_searches_left`; ScrapeCreators `https://api.scrapecreators.com/v1/credit-balance` → `creditCount`. Warn when Naver cafes are a main source (preview only). End with "이대로 할까요?" and stop.
3. Step 2 Gather, tool order: WebSearch → naver-search (blog/cafearticle/news/kin/local/datalab) → SerpAPI (only the allowed cases) → last30days (`--emit=json`, `--days 30` for current chatter, `--days 365` for durable info; Threads/YouTube) → kakao-map / airbnb. Respect budgets.
4. Step 3 Sponsor check: collect Naver blog URLs (≤ 30, most relevant/recent) → write to a temp file → run the script → use `verdict`, `evidence`, `excerpt`.
5. Step 4 Per-source extraction: tier, date, engagement, 강조한 장점 ≤ 3, 언급한 단점 ≤ 3 ("언급 없음" if none) — from `excerpt` for blogs, from the text for others. Sponsored → tier `D`.
6. Step 5 Cross-check: claim in ≥ 2 independent sources → "확인됨"; 1 → "한 곳만". Price/hours/rules older than 12 months → "오래된 정보".
7. Step 6 Report: skeleton §0–§4 from spec §7; §2 협찬 vs 실사용 always present (write "협찬글 없음" if none). Load the `artifact-design` skill before writing the page (and `artifact-diagramming` if a diagram helps); publish with the Artifact tool; save md to `~/Documents/search-reports/YYYY-MM-DD-<slug>.md`; reply with link + 3-line summary + actual usage (SerpAPI calls, credits spent).
8. Rules table: never drop sponsored posts; never invent links/numbers; every item has link + date; cafe posts preview-only; never print keys.

- [ ] **Step 1: Baseline (RED)** — fresh subagent, no skill: "알아봐줘: 성수동 브런치 카페 후기 모아줘" in this Mac's Claude Code; record whether it proposes a plan first, labels sponsorship, gives tiers/dates. Expected: none of these.
- [ ] **Step 2: Write SKILL.md** per the list above.
- [ ] **Step 3: Install link** — in `install-mac.sh` after the last30days block: if `~/.claude/skills/search` is a real directory, print a warning and skip; else `ln -sfn "$DIR/skills/search" "$HOME/.claude/skills/search"`. Run `bash search/install-mac.sh`; expect `~/.claude/skills/search -> …/dotfiles/search/skills/search`.
- [ ] **Step 4: GREEN check** — fresh subagent with the skill, same request, told to stop after Step 1. Expected: a plan with template, sources, expected usage, balances, cafe warning if relevant, ending "이대로 할까요?". Then a second subagent run continuing past the plan with "ㄱ" on a small topic, writing the md only (no Artifact publish): report has §0–§4, tiers, dates, at least one sponsor verdict from the script.
- [ ] **Step 5: Docs** — README 구성 표 row for `search` skill, file tree, root README line.
- [ ] **Step 6: Commit and push** — `feat(search): /search 스킬 — 틀 먼저 확인, 협찬 표시·장단점, 출처 등급, 교차 확인, 아티팩트 리포트`; `git push`.
