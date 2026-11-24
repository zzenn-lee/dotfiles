---
name: search
description: Use when the user asks to research/look up/compare/collect information for daily life — travel, shopping, products, venues, services, reviews, events — e.g. "/search", "알아봐줘", "찾아봐줘", "후기 모아줘", "정리해줘(검색)", "비교해줘".
argument-hint: "<무엇을 알아볼지>"
---

# Search

Collect information for a daily-life question from several kinds of sources, label who is
talking (official, real user, listicle, sponsored), and hand back one organized report as a
claude.ai Artifact link. The user makes the decision; the report shows the evidence.

**Request**: $ARGUMENTS

Instructions are in English; everything shown to the user is plain Korean (해요체).
Mac only, Claude Code only. No paid tools.

## Step 1: Plan — show it, then stop and wait

Every request gets a plan first, even a short or casual one ("후기 모아줘" included). Do not run
any search before the user answers. The plan is short, so it never costs the user much.

1. **Topic type → body template** (pick one; this becomes report §1):

| 요청 성격 | 본문 틀 |
|---|---|
| 일정·여행 | 날짜(또는 장소)별 표 + 주제별 팁 + 예약 시기·주의 |
| 상품 고르기 | 상품 비교 표(링크·가격·장점·단점·사이즈/핏) + 브랜드별 특징 |
| 업체·서비스 후기 | 업체별 후기 카드(좋았던 점·아쉬운 점·가격대) + 공통 불만 |
| 그 밖 | 질문을 하위 질문 3~5개로 나눠 질문별 정리 |

2. **Sources, each with a one-line reason.** Pick from this table; use at least one source per
   relevant row, not WebSearch alone:

| Source | Use for |
|---|---|
| `WebSearch` | general web, official pages (A tier), news — always first |
| `naver-search` MCP | Korean blog / cafearticle / news / kin / local / datalab |
| `serpapi` MCP | only: Korean-localized Google, Google Shopping / Hotels / Flights / Maps, `site:` search of a Korean community |
| `last30days` engine | Reddit, YouTube, HN, Threads (+ YouTube comments) — real-user chatter |
| `kakao-map` MCP | domestic places: address, category, coordinates |
| `airbnb` MCP | lodging listings and details |

   Typical mixes: 국내 장소·업체 → naver blog + cafe + local, kakao-map, WebSearch (공식) ·
   해외 여행 → WebSearch, last30days `--days 365`, serpapi hotels/flights, airbnb ·
   상품 → WebSearch (브랜드 공식), naver blog, serpapi shopping, last30days.
   Fast-changing local topics (요즘 뜨는 동네 맛집·카페, 팝업, 행사) → also offer last30days
   Threads as an *optional* source with its credit estimate (see 3.), and let the user choose.
   Instagram is never used.

3. **Expected usage vs budget.** Per-run budgets: SerpAPI ≤ 10 calls, ScrapeCreators ≤ 100
   credits, blog sponsor checks ≤ 30 posts. If the plan needs more, say how much more and why
   in the plan — the user's "ㄱ" is the OK.
   ScrapeCreators cost (measured 2026-11-24, ~1 credit per API request): Threads ≈ 1 credit
   per subquery · Reddit ≈ 10 credits per run when keyless Reddit is blocked from this network
   (the engine then falls back to paid search + comment fetches; it was blocked in testing) ·
   YouTube comments ≈ 1 credit per video. Estimate per last30days run from these and write the
   total in the plan.

4. **Current balances.** Run this (it reads keys from the file and prints only numbers; never
   `cat` the file, `echo` a key, or use `set -x`):

```bash
( set -a; . ~/.config/search/keys.env 2>/dev/null; set +a
  if [ -n "${SERPAPI_API_KEY:-}" ]; then
    curl -s "https://serpapi.com/account.json?api_key=${SERPAPI_API_KEY}" \
      | python3 -c 'import json,sys; print("SerpAPI 남은 횟수:", json.load(sys.stdin)["total_searches_left"])' 2>/dev/null \
      || echo "SerpAPI 남은 횟수: 조회 실패"
  else echo "SerpAPI: 키 없음 (serpapi 안 씀)"; fi
  if [ -n "${SCRAPECREATORS_API_KEY:-}" ]; then
    curl -s -H "x-api-key: ${SCRAPECREATORS_API_KEY}" "https://api.scrapecreators.com/v1/credit-balance" \
      | python3 -c 'import json,sys; print("ScrapeCreators 남은 크레딧:", json.load(sys.stdin)["creditCount"])' 2>/dev/null \
      || echo "ScrapeCreators 남은 크레딧: 조회 실패"
  else echo "ScrapeCreators: 키 없음 (Threads 못 봄, Reddit·YouTube·HN 은 됨)"; fi )
```

   Keep the two numbers: they are the "before" values for the usage line in Step 6.

5. **Naver cafe warning.** Whenever Naver cafes are a main source — 동네 맛집·카페, 육아,
   결혼 준비, 지역 커뮤니티, 중고 거래, and any other topic where cafe posts dominate — say so: "카페 글은 미리보기(제목·앞부분)만 보고 본문은 안 읽어요 —
   링크를 남길게요."

Plan output (Korean, this shape):

```markdown
**계획**
- 정리 틀: <template> — <one line why>
- 볼 곳:
  - <source> — <why>  (×N)
  - ...
- 예상 사용: WebSearch N회 · 네이버 N회 · SerpAPI N회(한도 10) · last30days N회(크레딧 ≤ N, 한도 100) · 블로그 협찬 판별 N개(한도 30)
- 지금 남은 양: SerpAPI <n>회 · ScrapeCreators <n>크레딧
- 주의: <cafe warning / budget overrun / missing key, or "없음">

이대로 할까요?
```

Stop after "이대로 할까요?". On "ㄱ"/yes → Step 2. On a change → show the revised plan only,
and ask again.

## Step 2: Gather

Run the planned sources in this order, and only the planned ones:

1. **WebSearch** — official pages first, then general results. Add query variants that surface
   first-hand posts: `<topic> 후기`, `<topic> 단점`, `<topic> 내돈내산`, plus an English query
   for overseas topics.
2. **naver-search** — `blog`, `cafearticle`, `news`, `kin`, `local`, `datalab` as the plan says.
   Keep every Naver blog URL (`blog.naver.com/…`) for Step 3. Cafe results (`cafe.naver.com/…`):
   keep title + preview + link + date only; do not open them.
   If you ever call a search API with curl instead of the MCP, pass Korean queries as
   `curl -G --data-urlencode "query=<검색어>" <endpoint>` (hand-encoded `%20` queries returned 0
   results in testing).
3. **serpapi** — only for the allowed cases above. Count every call; stop at the budget.
4. **last30days** — call its engine directly for JSON (not its own report format). Under Claude
   Code the engine refuses to run without a query plan (its "LAW 7" gate, exit 2), so always pass
   a small plan on stdin with `--plan -`, and restrict sources with `--search`. Shell variables do
   not survive between Bash calls, so do it all in one call and use the printed path afterwards:

```bash
L30PY=""
for py in python3.14 python3.13 python3.12 python3; do
  command -v "$py" >/dev/null && "$py" -I -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' && L30PY="$py" && break
done
if [ -z "$L30PY" ]; then echo "last30days: Python 3.12+ 없음 — 건너뜀"; else
  out="$(mktemp -t search-l30)"; echo "결과 파일: $out"
  "$L30PY" ~/.claude/skills/last30days/scripts/last30days.py '<topic>' --emit=json --days 30 \
    --search reddit,threads --plan - > "$out" 2> "$out.err" <<'PLAN_EOF'
{"intent": "opinion", "freshness_mode": "balanced_recent", "cluster_mode": "none",
 "subqueries": [{"label": "primary", "search_query": "<keywords>", "ranking_query": "<natural question>",
   "sources": ["reddit", "threads"], "weight": 1.0}]}
PLAN_EOF
  echo "exit=$?"; tail -3 "$out.err"
fi
```

   - Fill: `--search` and `sources` = the planned last30days sources (`reddit`, `threads`,
     `youtube`, `hackernews`; never `instagram`). `search_query` = short keywords, no dates;
     `intent` = `how_to` (tips) → `"freshness_mode": "evergreen_ok"`, `"cluster_mode": "workflow"`;
     otherwise `opinion` / `balanced_recent` / `none` as above. Up to 3 subqueries (e.g. Korean and
     English keywords for Threads — a Korean-only Threads query returned 0 results in testing).
   - `--days 30` for current chatter (trends, recent reviews); `--days 365` for durable info
     (trip tips, product reviews, a business's reputation). Bash timeout 600000.
   - Output: a JSON object; items are in `results[]` with `title`, `url`,
     `source`, `published_at`, `engagement`, `summary`. `source_status` says which sources ran.
   - If it prints "Python 3.12+ 없음 — 건너뜀" or `exit` ≠ 0: skip last30days and list it under §3
     한계 ("last30days 건너뜀: <reason>").
   - **Credits:** after every last30days call, re-run the Step 1 balance command. When
     (before − now) reaches 100 credits (or the amount the user OK'd), stop calling last30days.
   - For posts older than a year, supplement with serpapi `site:reddit.com` (counts toward the
     SerpAPI budget).
5. **kakao-map / airbnb** — place facts and listings as planned.

For each item keep: URL, title, source, date (as shown by the source), engagement if given
(공감·댓글·조회·upvotes), and the text or snippet you got.

## Step 3: Sponsor check (Naver blogs)

1. Cap: 30, unless the user approved a higher N (N ≤ 100) in the Step 1 plan — then use that N.
   From the Step 2 Naver blog URLs, pick up to that cap: first posts that name the specific venue
   or product being researched, then generic roundups ("추천 N곳"); within each group, most
   recent first.
2. In one Bash call, write them one per line to a temp file, run the script with `--max` set to
   the cap from 1 (30 by default, or the approved N up to 100), and print the result path:

```bash
f="$(mktemp -t search-blogs)"
printf '%s\n' '<url1>' '<url2>' > "$f"
python3 ~/.claude/skills/search/scripts/sponsor_check.py --input "$f" --max 30 > "$f.json"  # or --max <approved N, ≤ 100>
echo "판별 결과: $f.json"
```

3. Read the printed `판별 결과` path (Read tool, absolute path) — one object per URL: `verdict` (`협찬` | `의심` | `없음` | `읽기실패`),
   `evidence` (`[{signal, position}]` — the phrase/link and where: 맨 위·맨 아래·본문 중간),
   `excerpt` (~3,000 chars: start + end + paragraphs around 장점/단점 words), `date`, `title`.
4. Cafe posts never go into this script. Non-blog URLs come back `읽기실패` — that is expected.

## Step 4: Extract per source

For every kept item fill these slots:

| Slot | Rule |
|---|---|
| 등급 | `A 공식` operator/maker/public body · `B 실사용` independent first-hand · `C 정리글` listicle, SEO roundup, aggregator ("BEST 10"), or a post that says itself it is not a first-hand visit/use (comparison or price-list posts, AI-made images) — note "직접 경험 아님" · `D 협찬·광고` script verdict `협찬`, or a visible ad label. Verdict `의심` does **not** move the post to `D` — it keeps the tier (`B`/`C`) its content otherwise earns |
| 협찬 배지 | verdict `협찬` → tier `D` + one evidence line, e.g. "맨 아래: 소정의 원고료" · verdict `의심` → `협찬 의심` badge on top of its earned `B`/`C` tier (same evidence line) · `판별 못 함` for `읽기실패` · cafe: `미리보기만` |
| 날짜 | the post's date; if none, "날짜 없음" (never guess) |
| 반응 | engagement numbers if the source gives them, else "—" |
| 강조한 장점 | ≤ 3, short phrases |
| 언급한 단점 | ≤ 3; "언급 없음" if none |

Naver blogs: read only `excerpt` (do not re-read the full post). Other sources: the text or
snippet from Step 2. Sponsored (`협찬`) posts stay in the report with tier `D` — they are
labeled, not removed. `의심` posts stay at their earned `B`/`C` tier with a `협찬 의심` badge —
they are flagged, not demoted.

## Step 5: Cross-check

- Cross-check claim by claim. "확인됨" only when ≥ 2 independent sources state the same
  *specific* claim — a named dish or product, a price, a wait time, hours, a rule.
  Two posts by the same author or copies of one listicle count as one source. `D` sources do not
  confirm each other, and a `협찬 의심`-badged source never counts toward "확인됨" either (it may
  still appear as context in §2/§3).
- Found in only 1 source → "한 곳만". A shared vague impression ("분위기 좋음", "맛있어요") is
  "인상" even if many sources say it; it never becomes "확인됨".
- Price, hours or rules dated more than 12 months before today → "오래된 정보".
- Sources that contradict each other → list both sides with links in §3.

## Step 6: Report — Artifact + md

Write the report in this skeleton (Korean). Every item has a link and a date.

```markdown
# <주제> — 검색 정리 (<YYYY-MM-DD>)

## 0. 요약
- 찾은 것: <one or two sentences>
- 본 출처: 총 N곳 — A 공식 n · B 실사용 n · C 정리글 n · D 협찬·광고 n
- 협찬 의심 비율: 블로그 판별 N개 중 협찬 n · 의심 n (n%)
- 기준 날짜: <today>

## 1. 본문 — <template name>
<the Step 1 template; each item: 내용 · [출처](url) · 날짜 · 등급 배지 · 협찬 배지(해당 시) · 확인됨/한 곳만>

## 2. 협찬 vs 실사용
- 협찬·협찬 의심 글이 공통으로 강조한 점: …
- 협찬 의심 배지 없는 실사용(B/C) 후기의 평가: … (같은 점에 대해 맞는지·다른지)
- 협찬(또는 협찬 의심)글인데도 나온 단점: …
<if no 협찬/협찬 의심 posts were found: "협찬글 없음" + how many were checked>

## 3. 엇갈린 점·확인 못 한 것
- 소스끼리 다른 말: …
- 한 곳만 나온 주장: …
- 오래된 정보: …
- 한계: 카페 글은 미리보기만 봄 · 건너뛴 소스(키 없음, Python 3.12+ 없음, 크레딧 한도 등) · 이미지 속 협찬 배너는 못 읽음(판별 "없음"이어도 100% 아님) · <읽기실패 n개>

## 4. 출처 목록
| # | 제목 | 출처 | 등급 | 날짜 | 협찬 | 링크 |
```

Then:

1. Save the md to `~/Documents/search-reports/YYYY-MM-DD-<slug>.md` (`mkdir -p` first;
   `<slug>` = short kebab-case topic, romanized or Korean).
2. Load the `artifact-design` skill (and `artifact-diagramming` if a diagram helps, e.g. a
   route or a timeline) before writing the HTML page. Same sections §0–§4; tier and sponsor
   badges as visible labels.
3. Publish with the Artifact tool.
4. Re-run the Step 1 balance command for the "after" values.
5. Reply in Korean with exactly:

```markdown
<Artifact link>
- <요약 1>
- <요약 2>
- <요약 3>
사용: SerpAPI N회 (남은 n) · ScrapeCreators N크레딧 (남은 n) · 블로그 판별 N개 · md: <path>
```

## Rules

| Rule | Why |
|---|---|
| Never drop a sponsored post — keep it with tier `D` and its evidence | The user compares 협찬 vs 실사용 in §2 |
| Never invent a link, date, price or number; missing → "날짜 없음"/"—" | The report is evidence, not a guess |
| Every item has a link and a date | So the user can check it |
| Naver cafe posts: preview only, never read in full, never sponsor-checked | Member-only content; stated in §3 |
| Never print, echo or commit API keys | Keys live only in `~/.config/search/keys.env` |
| Stay within budgets unless the plan said otherwise and the user said "ㄱ" | Free quotas run out |

## Common mistakes

| Mistake | Instead |
|---|---|
| Searching right away because the request "looks short" | Step 1 plan for every request, end with "이대로 할까요?", wait |
| WebSearch only — results dominated by listicles (C) | Add naver blog/cafe, kakao-map, last30days per the source table; query `후기`/`단점`/`내돈내산` |
| Guessing sponsorship from the site type ("목록 글이니 광고일 듯") | Run `sponsor_check.py`; quote `evidence` with its position |
| Ad-hoc trust words ("신뢰도 중") | Exactly `A 공식` / `B 실사용` / `C 정리글` / `D 협찬·광고` |
| Moving a `의심` post to tier `D` | Only verdict `협찬` (or a visible ad label) → `D`; `의심` keeps its earned `B`/`C` tier + `협찬 의심` badge |
| Counting a `협찬 의심` source toward "확인됨" | `의심` sources never confirm a claim, same as `D` |
| "날짜 미표기" for everything | Take the date from the source / script `date`; "날짜 없음" only when truly missing |
| Only pros, or a vague summary per place | 강조한 장점 ≤ 3 and 언급한 단점 ≤ 3 per source, "언급 없음" if none |
| Skipping §2 or §3 when there's little to say | §2 says "협찬글 없음"; §3 lists at least the limits |
| Plain chat answer | Artifact link + md file + 3-line summary + usage line |
| Reading full blog posts again in Step 4 | Use the script's `excerpt` |
| "확인됨" for a shared vibe ("분위기 좋음") | Only for the same specific claim in ≥ 2 independent sources; vibes are "인상" |
| last30days run without `--plan -` (exits 2 under Claude Code) | Use the Step 2 block: plan heredoc + `--search` |
| Reusing `$out` / `$f` in a later Bash call | Read the absolute path the block printed |
| Using last30days' own report format | `--emit=json`, merge its items into this report |
