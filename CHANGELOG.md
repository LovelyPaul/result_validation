# Changelog

All notable changes to this plugin are documented here (Keep a Changelog style).

## [0.2.0] - 2026-07-20
### Added
- **루트 에이전트 어댑터**: `CLAUDE.md`(= `@AGENTS.md` 포인터 1줄) + `AGENTS.md`(RUNBOOK 정본
  선언 + **변형 오프닝** — 첫 입력이 연구 질문이면 파일·웹 없이 맨몸으로 답하고, 그 답을
  튜토리얼의 맨몸 대조 재료로 쓰도록 안내). 타 에이전트(Codex 등)도 같은 정본으로 진행 가능.
- **RUNBOOK §0.5 사전 점검 업그레이드**(wiki-demo 규격): OS·python 실측 명령을 Windows
  PowerShell·Unix bash 양쪽으로 제시, 맨몸 대조용 LLM 도구(codex·claude·gemini·ollama)를
  `command -v`/`Get-Command`로 실측해 **관측된 도구만** 선택지 제시(웹 챗 복붙 폴백 포함),
  오염 가드(원문을 읽은 진행 세션의 즉석 맨몸 요약 금지) 명문화.
- **RUNBOOK §3.5 산출물 규약 신설**: 산출물은 사용자 워크스페이스 `artifacts/` 또는
  `40-drafts/`에만 — 플러그인 폴더(`${CLAUDE_PLUGIN_ROOT}`) 쓰기 금지, 이전 산출물은
  삭제 대신 `artifacts/prev-<날짜>/` 보존.
- **workspace-standards 명시 참조**: RUNBOOK 환경 전제·init SKILL.md에 표준 문서 경로 명기 —
  10단위 넘버링(`01-FOLDER_NUMBERING.md`)·CLAUDE.md 12섹션(`04-CLAUDE_MD_GUIDE.md`)·
  하네스 7-layer(`06-CLAUDE_CODE_AGENT_METHODOLOGY.md` §8). init 템플릿 워크스페이스가
  표준 정합임을 재확인(CLAUDE.md 12섹션 실측).
### Changed
- RUNBOOK 진행 톤 규약 보강(wiki-demo 실측 교훈 반영): 톤 적용 범위 = 운영 브리핑 포함 모든
  산문 출력, 개인 말투 규칙보다 우선, 자기-계속 멘트 금지 사례 구체화, LaTeX 대체 표기(유니코드) 안내.
- `plugin.json` version 0.2.0. README 2종(영·한) 신규 기능 동기화.

## [0.1.0] - 2026-07-18
### Added
- 초기 릴리스. `/research-survey` 커맨드(라우터) + 3 스킬(main·init·run).
- 정본 대본 `RUNBOOK.md`(분 단위 튜토리얼) + references 6종(phase_contracts·taxonomy_dial·
  quality_gates·roles·citation_rules).
- **동봉 자립형 스크립트**(python3 stdlib): `skills/research-survey-run/scripts/classify.py`
  (범용 코퍼스 결정론 분류·랭킹·--sample) + `verify_summaries.py`(요약 결정론 검수).
- assets/templates: taxonomy 다이얼 · 서베이 섹션 · 자립형 대조표 HTML · workspace-standards
  준수 예시 워크스페이스(10단위 넘버링·CLAUDE.md **12섹션**·메타파일·`00-system/data-dictionary.md`).
- examples: ICML 2026 worked example(6,628편·9카테고리, 실제 편수·판정·사고 대응).
### Design
- 어댑터 층 아키텍처(정본 RUNBOOK + thin wrapper) — wiki-demo 참고.
- gptaku-plugins 규격 준수(plugin.json·`${CLAUDE_PLUGIN_ROOT}` 경로·README 이중언어).
- 범용 코퍼스 스키마(id/title/abstract/keywords?/url?/flags?)로 도메인 비결합 — 학회/arXiv 매핑만으로 동작.
- 콘텐츠 출처: DEV_TEAM ICML2026 서베이 실운영 기록(DEV_TEAM_PLAYBOOK.md).
- **`.claude-plugin/marketplace.json`** 추가 — 로컬 단일-플러그인 마켓플레이스(self-ref `source:"."`)로
  `claude plugin marketplace add <dir>` 원스텝 로컬 설치 지원.
### Verified
- cold-read 검수 루프(producer≠evaluator): worker 1차 FAIL(F1 스크립트 미패키징·F2 ICML 결합·
  F3 CLAUDE.md 12섹션 거짓·F4~F6) → master 수정 → worker 재검수 **PASS**(F1~F6 전건 해소,
  classify/verify 자립 실행 실측, end-to-end 새 사용자 자립 가능).
- **fresh 세션 설치 테스트 PASS**(격리 config dir): `claude plugin validate`✔ → `marketplace add`✔ →
  `install`✔(enabled) → `details`(4컴포넌트·~690tok) → `/research-survey help` 커맨드 라우팅·
  `${CLAUDE_PLUGIN_ROOT}` 해소 정상 → 자연어 자동발동으로 `research-survey-main` 스킬 발동·RUNBOOK 실행 확인.
