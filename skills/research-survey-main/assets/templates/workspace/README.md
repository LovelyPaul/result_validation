# <프로젝트명> — 연구 서베이 워크스페이스

관심 연구 주제로 논문을 지속 서베이하는 전용 작업공간. `research-survey` 플러그인으로 생성됨
(workspace-standards 10단위 넘버링 준수).

## 시작
1. `00-system/`의 taxonomy 다이얼에 관심 주제(카테고리)를 정의한다.
2. `60-data/`에 코퍼스(제목·초록·PDF)를 둔다.
3. `/research-survey run <카테고리>`로 한 사이클(추출→요약→검증→정리)을 돌린다.

## 구조
`CLAUDE.md`(운영 규약·12섹션) · `PROJECT_STATUS.md`(진행 현황) · `CHANGELOG.md`(변경 이력) ·
`00-system`~`90-archive`(10단위 넘버링) · `.claude/`(커맨드·에이전트·스킬).

## 원칙
증거 기반 완료 · producer≠evaluator · 환각0 · 축적 · 결정론 환원. 상세는 `CLAUDE.md`.
