---
name: research-survey
description: "논문 서베이·연구 정리·리서치 토픽 추적 요청에 사용합니다. '연구 서베이 / 논문 정리 / research survey / 서베이 튜토리얼 / ICML 논문 정리 / 관심 주제 논문 모아줘 / 지속 서베이 셋업' 같은 발화에 발동합니다. 단, 단발성 심층 리서치(웹 다중소스 조사) 요청이면 /deep-research 를, PRD·기획 문서 작성이면 /show-me-the-prd 를 사용합니다."
argument-hint: "[tutorial | demo | init <주제> | run <카테고리> | team-compare | help]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /research-survey — 관심 주제 연구 서베이 파이프라인

당신은 이 커맨드로 **연구 서베이 워크플로우**를 진행한다. 논문 코퍼스(학회 스냅샷 또는 arXiv
흐름)를 **관심 연구 주제(taxonomy 다이얼)**로 추출→요약→3중검증→인사이트·가설·서베이로
정리하고 Notion·wiki에 축적하는 전 과정을, 사용자가 배우고(튜토리얼) 직접 돌릴 수 있게 안내한다.

이 커맨드는 **얇은 라우터**다. 인자에 따라 아래 스킬로 분기하고, 각 스킬의 SKILL.md 절차를 따른다.
경로 참조는 항상 `${CLAUDE_PLUGIN_ROOT}/...` 를 쓴다(절대경로 하드코딩 금지).

## 인자 라우팅

| 인자 | 분기 | 스킬 | 설명 |
|---|---|---|---|
| `tutorial` (또는 인자 없음) | 튜토리얼 진행 | `research-survey-main` | 정본 `references/RUNBOOK.md`를 읽고 단계별 라이브 튜토리얼 진행 |
| `demo` | toy 가이드 체험 | `research-survey-main` | 정본 `references/DEMO.md` — 설치 직후 샘플만으로 추출→위키 검색→검수 거부 2종→승격을 가이드 진행(5~10분·각 단계 질문 종료) |
| `init <주제>` | 워크스페이스 생성 | `research-survey-init` | workspace-standards 준수 서베이 워크스페이스 스캐폴딩 |
| `run <카테고리>` | 한 사이클 실행 | `research-survey-run` | 지정 카테고리를 추출→요약→검증→정리까지 1사이클 |
| `team-compare` | 멀티 LLM 팀 비교 실습 랩 | `research-survey-main` | 정본 `references/TEAM_COMPARE.md` — 교차 벤더 리뷰(producer/reviewer)를 나란히 돌려 결정론 채점으로 비교. 기본 dry-run(비용 가드)·`--yes`로 실행 |
| `help` | 도움말 | (이 파일) | 아래 개요 출력 |

## 발동 시 즉시 (문서만 읽고 끝내지 말 것 — 실행하라)

1. 인자를 파싱한다. 인자가 없거나 `tutorial`이면 `research-survey-main` 스킬을 발동해
   `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/references/RUNBOOK.md`의 §0 인트로부터 진행한다.
   `demo`면 `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/references/DEMO.md`를 읽고
   ①~⑥ 흐름을 가이드 진행한다(각 단계 배너로 시작해 질문으로 종료 — 자기-계속 금지,
   대상 폴더 등 선택은 AskUserQuestion).
2. `init`이면 대상 주제를 확인하고(모호하면 AskUserQuestion 툴 JSON으로 질문 — 텍스트 질문 금지)
   `research-survey-init` 스킬로 워크스페이스를 만든다.
3. `run`이면 대상 카테고리를 확인하고 `research-survey-run` 스킬로 1사이클을 돌린다.
4. `team-compare`면 `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/references/TEAM_COMPARE.md`를
   읽고 ①~④ 흐름을 가이드 진행한다(기본 dry-run으로 호출 수·비용을 먼저 보이고, 진행 여부를
   AskUserQuestion으로 물은 뒤에만 `--yes` 실행 — 각 단계 질문 종료).

## 개요 (help)

**무엇을 배우나**: "맨몸 LLM 요약"과 "근거가 추적되는 서베이"가 어떻게 다른지 —
관심 주제를 다이얼로 정의하고(taxonomy), 결정론 분류로 추출하고, 논문 PDF를 실측 요약하고,
producer≠evaluator 3중 검증으로 환각을 거르고, 인사이트·가설·서베이로 축적하는 전 과정.

**핵심 원칙 5**: ①증거 기반 완료 ②producer≠evaluator ③환각0(출처만이 사실) ④축적(살아남는
아티팩트) ⑤결정론 환원(카운트·게이트는 스크립트 출력으로만). 상세는
`${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/references/quality_gates.md`.

**worked example**: `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/examples/icml2026-worked-example.md`
(ICML 2026 6,628편을 9카테고리로 서베이한 실제 사례 — 편수·판정·사고 대응 포함).
