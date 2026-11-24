# search

여러 곳(네이버, 구글, 소셜, 지도, 숙소, 항공)에서 정보를 모아 오는 도구 묶음이에요. macOS 용이고, 무료 또는 무료 한도 안에서만 써요.

## 설치

```bash
bash search/install-mac.sh                    # 처음 한 번: 키 파일을 만들고, 키 없는 도구부터 등록
bash search/bin/set-key KAKAO_REST_API_KEY    # 키 하나 넣기: 화면에 안 보이게 입력 → 저장 → 자동 재등록
bash search/bin/set-key                       # 넣을 수 있는 키 이름 목록
```

편집기로 한 번에 채워도 돼요: `open -e ~/.config/search/keys.env` 후 `bash search/install-mac.sh`. 키 발급 방법은 그 파일 주석에 있어요.

새 Claude Code 세션에서 `/mcp` 로 연결 상태를 확인해요.

## 구성

| 이름 | 종류 | 맡는 곳 | 키 | 버전 |
|---|---|---|---|---|
| naver-search | MCP | 네이버 블로그·카페·뉴스·지식인·지역, DataLab 트렌드 | 네이버 API HUB | `@isnow890/naver-search-mcp@1.1.0` |
| naver-blog | MCP (기존, 별도 저장소) | 네이버 블로그 본문 전체 읽기 | — | `~/workspace/naver-blog-mcp` |
| kakao-map | MCP | 국내 장소·주소·좌표 | 카카오 REST | `mcp-server-kakao-map@0.3.2` |
| serpapi | MCP (원격) | 구글 웹·쇼핑·호텔·항공·지도 | SerpAPI (무료 월 250회) | 호스티드 `mcp.serpapi.com` |
| google-maps | MCP (원격, 공식) | 해외 장소·경로·날씨 | Google Cloud (결제 계정 필요) | Maps Grounding Lite |
| airbnb | MCP | Airbnb 숙소 검색·상세 | — | `@openbnb/mcp-server-airbnb@0.3.0` |
| reddit | MCP | Reddit 검색·댓글 | 이미 승인된 Reddit 키 (신규 발급 불가) | `reddit-mcp-buddy@1.3.0` |
| fli | MCP | 구글 항공권 (가장 싼 날짜 찾기) | — | `flights[all]==0.9.0` — **지금은 꺼 둠** |
| last30days | 스킬 | Reddit·YouTube·HN 무료, Instagram·Threads·TikTok 은 ScrapeCreators 키 | 선택 | `mvanhorn/last30days-skill` (최신) |

## 파일

```
search/
├─ install-mac.sh     설치·등록 (여러 번 실행해도 됨)
├─ keys.env.example   키 목록 템플릿 → ~/.config/search/keys.env 로 복사돼요
├─ bin/mcp            MCP 런처: 키 파일을 읽고 이름에 맞는 서버를 고정 버전으로 실행
└─ bin/set-key        키 하나를 숨김 입력으로 저장하고 설치를 다시 실행
```

- 키는 `~/.config/search/keys.env` 한 곳에만 있어요 (권한 600, git 에 안 올라감). Claude 설정 파일에는 키가 들어가지 않아요.
- last30days 는 자기 `~/.config/last30days/.env` 를 읽어서, 설치 스크립트가 해당 키만 옮겨 적어요.
- 버전을 올리려면 `bin/mcp` 의 버전 숫자를 바꾸면 돼요.

## 알아 둘 것

- **fli 장애:** 2026-11 현재 구글 쪽 변경으로 모든 검색이 0건이에요 ([#270](https://github.com/punitarani/fli/issues/270)). 고쳐지면 `FLI_ENABLE=1 bash search/install-mac.sh`. 그전엔 serpapi 의 구글 항공권을 써요.
- **네이버:** 예전 개발자센터 키는 2027-06-30 에 끊겨요. 네이버 쇼핑 검색 API 는 2026-07-31 에 종료됐어요.
- **쓰지 않는 것:** 스카이스캐너·부킹닷컴·익스피디아 공식 MCP (파트너 전용), Amadeus (2026-07 종료), Apify 등 유료 크롤러.
- 네이버·카카오 장소 리뷰, 야놀자·여기어때는 API 가 없어요.
