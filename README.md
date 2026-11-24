# dotfiles

Claude Code 같은 AI 에이전트 설정(규칙, 스킬, hook)을 Mac·Windows에서 같이 쓰려고 모아 둔 저장소예요.

## 구조

```
claude/
└─ skills/
   └─ explain/SKILL.md   /explain — 코드나 변경을 위에서 아래로(목적 → 아키텍처 → 파일 트리 → 세부) 한 번에 설명
```

예정: `claude/CLAUDE.md`(전역 규칙), `claude/hooks/`(설명 빠뜨림 방지 Stop hook)

## 설치

스킬 폴더를 `~/.claude/skills/` 아래에 링크해요.

Mac
```bash
ln -s "$PWD/claude/skills/explain" ~/.claude/skills/explain
```

Windows (PowerShell, 관리자 또는 개발자 모드)
```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\explain" -Target "$PWD\claude\skills\explain"
```
