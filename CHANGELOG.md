# Changelog

All notable changes to this plugin are documented here (Keep a Changelog style).

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
