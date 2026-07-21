---
name: research-survey-init
description: This skill scaffolds a standards-compliant research survey workspace. Use when a user wants to set up/start a new survey project or workspace for a research topic. Example triggers — "/research-survey init", "서베이 워크스페이스 만들어", "연구 서베이 프로젝트 셋업", "리서치 워크스페이스 초기화", "init survey workspace", "새 서베이 시작".
---

# research-survey-init — 서베이 워크스페이스 스캐폴딩

workspace-standards(10단위 넘버링·CLAUDE.md 12섹션·메타파일)를 준수하는 연구 서베이 전용
워크스페이스를 만든다. 템플릿은 `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/assets/templates/workspace/`.

**표준 베이스캠프 = workspace-standards** (템플릿이 이 표준을 준수하며, 이탈 시 `_meta/deviations.md`에 기록.
아래 요지만으로 표준 리포 없이 이해·진행 가능):
- **10단위 폴더 넘버링**(00~90) — 폴더는 2자리 숫자 접두(`00-system/`~`90-archive/`)로 시작:
  정렬 보장·중간 삽입 여유·혼용 금지. 원문: `workspace-standards/01-FOLDER_NUMBERING.md`
- **CLAUDE.md 12섹션 스키마** — ①제목+한 줄 ②대상 런타임 ③정체성(허용/금지) ④핵심 원칙
  ⑤폴더 구조 ⑥워크플로우 ⑦커맨드 ⑧Scale Modes ⑨트리거 경계 ⑩도메인 프레임워크
  ⑪산출물 형식 ⑫품질 규칙+변경 이력. 원문: `workspace-standards/04-CLAUDE_MD_GUIDE.md`
- **"워크스페이스 = 하네스" 7-layer** — instruction surface(CLAUDE.md)·commands·agents·skills·
  hooks·state·memory 7층 = 하나의 특화 에이전트. 원문:
  `workspace-standards/06-CLAUDE_CODE_AGENT_METHODOLOGY.md` §8.1. 하네스 강도 4단계
  (basic/runtime-ready/runtime-enforced/meta-harness)는 같은 문서 §8.2

## 발동 시 즉시

1. 대상을 확인한다 — **AskUserQuestion 툴 JSON으로** 묻는다(텍스트 질문 금지):
   - 프로젝트명(폴더명, kebab-case)
   - 생성 위치(기본: 현재 작업 디렉토리 하위)
   - 관심 주제(카테고리 1개 이상 — taxonomy 다이얼 시드)
   - 하네스 강도(basic[기본] / runtime-ready) — roles.md 참조
2. 템플릿 워크스페이스를 대상 경로로 복사한다:
   ```
   원본: ${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/assets/templates/workspace/
   대상: <위치>/<프로젝트명>/
   ```
   포함: `CLAUDE.md`·`AGENTS.md`(세션 시작 자기소개 어댑터 — CLAUDE.md가 `@AGENTS.md`로
   참조)·`README.md`·`PROJECT_STATUS.md`·`CHANGELOG.md`·`.gitignore`·`_meta/deviations.md` +
   `00-system`~`90-archive`(10단위, 빈 폴더는 `.gitkeep`) + `.claude/{commands,agents,skills}`.
3. **치환**: `<프로젝트명>`은 `CLAUDE.md`·`AGENTS.md`·`README.md`에서, `<YYYY-MM-DD>`는 `CHANGELOG.md`에서
   실제 값으로(오늘 날짜는 `date`/`Get-Date`로 실측 — 추정 금지). `00-system/`에 `taxonomy.json`을
   `templates/taxonomy.template.json`에서 복사하고 관심 주제를 카테고리로 시드(`example-topic`은 교체).
4. `30-templates/`에 `TEMPLATE_survey.md`(= survey_section.md)와 대조표 HTML을 배치.
   `00-system/`에 `data-dictionary.md`(코퍼스 스키마)가 포함됐는지 확인.
5. `.claude/settings.local.json`을 생성한다(gitignore 대상 — 권한 시드):
   `{ "permissions": { "allow": ["Bash", "Read", "Write"], "deny": [] } }`.
6. `CHANGELOG.md`에 "워크스페이스 생성" 1줄, `PROJECT_STATUS.md`에 "taxonomy 다이얼 정의 = 진행중".
7. 완료 후 다음 액션을 안내(질문으로 종료): "코퍼스를 `60-data/corpus.json`(범용 스키마)로 두고
   `/research-survey run <카테고리>`로 첫 사이클을 돌릴까요?"

## 규약
- 넘버링/비넘버링 혼용 금지. 빈 폴더 `.gitkeep` 유지. 파일명 규약(시스템 UPPERCASE·지식베이스 `NN_`·
  템플릿 `TEMPLATE_`) 준수. 표준 이탈은 `_meta/deviations.md`에 기록.
- 경로는 `${CLAUDE_PLUGIN_ROOT}`. 대상 워크스페이스 밖은 건드리지 않는다.
