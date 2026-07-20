---
title: research-survey DEMO (toy 실행 워크플로우 정본)
version: 0.4.0
duration: 5-10분
role: 진행자(에이전트)가 이 대본대로 자동 진행 — 설치 직후 "LLM-wiki 검색·검수가 실제로 되는가"를 체험시킨다
---

# DEMO — 설치 직후 toy 체험 (정본)

> `/research-survey demo`의 정본. 목적: 새 사용자가 **자기 데이터 없이** 동봉 샘플만으로
> ①추출 ②위키 검색 ③검수 게이트 ④정본 승격을 눈으로 확인한다. 진행 톤·산출물 규약은
> RUNBOOK 정본을 따른다(각 단계 배너 + 질문 종료·LaTeX 금지·플러그인 폴더 쓰기 금지).

## 진행 흐름 (① → ⑥ 자동, 각 단계 사이 질문으로 통제권 반환)

**① 워크스페이스 스캐폴드** — `▶ [1/6] 준비 — 데모용 워크스페이스를 만듭니다`
- 대상 폴더를 **AskUserQuestion으로** 묻는다(기본: 현재 폴더 하위 `research-survey-demo/`).
  AskUserQuestion 툴이 없는 에이전트는 텍스트로 묻는다.
- `research-survey-init` 스킬 절차를 재사용해 표준 워크스페이스를 스캐폴드한다
  (10단위 넘버링·CLAUDE.md 12섹션 — 템플릿 그대로).

**② 샘플 데이터 자동 복사** — `▶ [2/6] 샘플 — 검증된 15편 코퍼스와 위키 노트 3개를 넣습니다`
- `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/assets/templates/workspace/` 에서:
  - `60-data/corpus.sample.json` → 워크스페이스 `60-data/corpus.json`
  - `00-system/taxonomy.sample.json` → 워크스페이스 `00-system/taxonomy.json`
  - 샘플 노트 **3개 파일을 명시 지정 복사** — `20-knowledge-base/wiki/notes/` 의
    `deer-benchmark.md`·`selfcheckgpt.md`·`llm-as-a-judge.md` **만** 워크스페이스 같은 경로로.
    ⚠ `*.md` 글롭 복사 금지 — 템플릿 폴더의 `README.md`(frontmatter 없음)가 노트로 혼입된다.
- 멘트: "코퍼스 15편은 전건 arXiv 실측 검증본입니다 — 관련 7편(평가·할루시네이션 검출)과
  무관 8편(비전 토큰압축 등)이 섞여 있어요. 다이얼이 이걸 갈라내는 걸 보시게 됩니다."

**③ 결정론 분류** — `▶ [3/6] 추출 — 다이얼이 관련 논문만 골라냅니다`
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/classify.py" --workspace .
```
- 기대: `research-review-harness 7편` — 관련 7편 전부·무관 0편(재현율 100%·오탐 0).
- `70-analysis/categories/research-review-harness.md`를 열어 편수·랭킹을 화면에 보인다.

**④ 위키 검색 시연** — `▶ [4/6] 검색 — 위키가 근거 발췌로 답합니다`
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/wiki_index.py" --workspace .
python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/wiki_query.py" --workspace . "DEER 평가 프레임워크는 보고서를 어떻게 평가하나"
```
- 기대: 색인 3건(엣지·감사 리포트 포함) → 리포트 1위 `[[deer-benchmark]]` — 7 dimensions·
  101 rubric items 같은 수치가 **출처(arXiv id)와 함께** 발췌된다.
- 멘트: "맨몸 LLM이라면 그럴듯하게 답했겠지만, 위키는 검증해 쌓아둔 노트의 근거 발췌로 답합니다."

**⑤ 검수 게이트 시연 (2종 — 일부러 실패시킨다)** — `▶ [5/6] 검수 — 틀린 산출물이 거부되는 걸 봅니다`
1. **출처 없는 산출물**: `40-drafts/demo-bad.md`(frontmatter는 갖췄지만 출처 인용 0)를 만들어
   `wiki_promote.py --workspace . 40-drafts/demo-bad.md --apply` → **거부**(B8 lint) + 정본 미생성 확인.
2. **Timeline 변조**: 샘플 노트 하나를 복사해 기존 Timeline 항목을 살짝 바꾼 산출물로 승격 시도
   → **거부**(E1 append-only) 확인.
- 멘트: "게이트는 '그럴듯함'을 안 봅니다 — 출처가 없거나 이력을 고치면 기계가 막습니다."

**⑥ 정상 승격** — `▶ [6/6] 승격 — 검증된 산출물만 정본이 됩니다`
- 출처를 갖춘 데모 노트(`40-drafts/demo-note.md`, 2분할+필수키+arXiv 인용)를 만들어:
  dry-run(diff 미리보기) → 사용자에게 승인 질문 → `--apply` → `promotion-manifest.jsonl` 기록 확인.
- 재검색 1회(`wiki_query`)로 방금 승격한 노트가 검색되는 것까지 보여주면 완결.

## 마무리 멘트 + 다음 단계 질문 (데모의 마지막 발화)

> 방금 보신 전 과정 — 추출·검색·검수·승격 — 이 전부 **여러분 주제로 그대로** 돌아갑니다.
> RUNBOOK의 "자기 주제로 바꾸기" 절대로: ①taxonomy.json 다이얼을 관심 주제로 수정
> ②`corpus_fetch.py`로 원하는 논문 반입(arXiv id 또는 검색어) ③classify 재실행.
> 지금 관심 주제로 바꿔볼까요, 아니면 데모 워크스페이스를 정리할까요?

## 안전핀 (RUNBOOK §3.5·§4 준수)
- 산출물은 데모 워크스페이스 안에만 — 플러그인 폴더(`${CLAUDE_PLUGIN_ROOT}`)에 쓰지 않는다.
- ⑤의 실패 시연 산출물도 워크스페이스 `40-drafts/`에만 만들고, 삭제하지 않는다(회고 재료).
- 라이브가 어긋나면 RUNBOOK §2 캡처 전환 규약대로 정직하게 알리고 진행.
