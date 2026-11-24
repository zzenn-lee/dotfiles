#!/usr/bin/env bash
# search 도구 설치 (macOS). 여러 번 실행해도 돼요 — 키를 채운 뒤 다시 실행하면 새 도구만 더 등록돼요.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
KEYS="$HOME/.config/search/keys.env"

# 1. 키 파일 (없을 때만 예시에서 만들기)
mkdir -p "$(dirname "$KEYS")"
if [[ ! -f "$KEYS" ]]; then cp "$DIR/keys.env.example" "$KEYS"; echo "키 파일 생성: $KEYS"; fi
chmod 600 "$KEYS"
set -a; . "$KEYS"; set +a

# 2. 실행 도구
command -v uv >/dev/null || { echo "uv 가 필요해요: brew install uv"; exit 1; }
command -v npx >/dev/null || { echo "Node.js 20+ 가 필요해요: brew install node"; exit 1; }
uv tool install --force --quiet "flights[all]==0.9.0"
command -v yt-dlp >/dev/null || uv tool install --quiet yt-dlp   # last30days 의 YouTube 자막용

# 3. last30days 스킬 (Claude Code 전역)
if [[ ! -e "$HOME/.claude/skills/last30days" && ! -e "$HOME/.agents/skills/last30days" ]]; then
  npx -y skills add mvanhorn/last30days-skill -g -a claude-code -s last30days -y
fi
# last30days 는 자기 .env 를 읽어요 → 키 파일의 해당 값만 옮겨 적기 (다른 줄은 건드리지 않음)
L30="$HOME/.config/last30days/.env"; mkdir -p "$(dirname "$L30")"; touch "$L30"; chmod 600 "$L30"
for k in SCRAPECREATORS_API_KEY BRAVE_API_KEY; do
  v="${!k:-}"; [[ -z "$v" ]] && continue
  grep -v "^$k=" "$L30" > "$L30.tmp" || true; echo "$k=$v" >> "$L30.tmp"; mv "$L30.tmp" "$L30"; chmod 600 "$L30"
done

# last30days 가 기본으로 볼 추가 소스 (Reddit·YouTube·HN 은 원래 켜져 있음). 이미 정해 뒀으면 건드리지 않음.
# Instagram 은 영상 위주라 뺐어요. 보충 검색(SC_MIN_ITEMS=0)은 무료 결과가 0건일 때만 크레딧을 써요.
grep -q '^INCLUDE_SOURCES=' "$L30" || echo "INCLUDE_SOURCES=threads,youtube_comments" >> "$L30"
grep -q '^LAST30DAYS_REDDIT_SC_MIN_ITEMS=' "$L30" || echo "LAST30DAYS_REDDIT_SC_MIN_ITEMS=0" >> "$L30"
grep -q '^LAST30DAYS_YT_SC_MIN_ITEMS=' "$L30" || echo "LAST30DAYS_YT_SC_MIN_ITEMS=0" >> "$L30"

# /search 스킬 (Claude Code 전역) — 이 저장소 폴더로 링크. 같은 이름의 진짜 폴더가 있으면 건드리지 않아요.
SEARCH_SKILL="$HOME/.claude/skills/search"
mkdir -p "$HOME/.claude/skills"
if [[ -d "$SEARCH_SKILL" && ! -L "$SEARCH_SKILL" ]]; then
  echo "⚠ $SEARCH_SKILL 가 이미 진짜 폴더라 링크를 건너뛰어요. 옮기거나 지운 뒤 다시 실행하세요."
else
  ln -sfn "$DIR/skills/search" "$SEARCH_SKILL"
fi

# 4. MCP 등록 (키가 있는 것만)
has() { for k in "$@"; do [[ -n "${!k:-}" ]] || return 1; done; }
reg() {
  claude mcp remove -s user "$1" >/dev/null 2>&1 || true
  claude mcp add -s user "$1" -- bash "$DIR/bin/mcp" "$1" >/dev/null && echo "  ✅ $1"
}
skip() { claude mcp remove -s user "$1" >/dev/null 2>&1 || true; echo "  ⏭  $1 — 키 없음: $2"; }

echo "MCP 등록:"
reg airbnb
# fli: 2026-11 현재 구글 쪽 변경으로 모든 검색이 0건 (github.com/punitarani/fli/issues/270).
# 고쳐지면 FLI_ENABLE=1 bash install-mac.sh 로 등록하세요. 그전엔 serpapi 의 google_flights 를 쓰세요.
if [[ "${FLI_ENABLE:-0}" == 1 ]]; then reg fli; else skip fli "구글 항공권 쪽 장애(#270) — FLI_ENABLE=1 로 켜기"; fi
if has NCP_APIGW_API_KEY_ID NCP_APIGW_API_KEY || has NAVER_CLIENT_ID NAVER_CLIENT_SECRET; then reg naver-search; else skip naver-search "NCP_APIGW_API_KEY_ID/KEY"; fi
if has KAKAO_REST_API_KEY;   then reg kakao-map;   else skip kakao-map   KAKAO_REST_API_KEY; fi
if has SERPAPI_API_KEY;      then reg serpapi;     else skip serpapi     SERPAPI_API_KEY; fi
if has GOOGLE_MAPS_API_KEY;  then reg google-maps; else skip google-maps GOOGLE_MAPS_API_KEY; fi
if has REDDIT_CLIENT_ID REDDIT_CLIENT_SECRET; then reg reddit; else skip reddit "REDDIT_CLIENT_ID/SECRET"; fi
echo "완료. 새 Claude Code 세션에서 /mcp 로 연결 상태를 확인하세요."
