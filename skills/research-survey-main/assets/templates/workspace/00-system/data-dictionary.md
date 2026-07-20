# data-dictionary — 범용 코퍼스 스키마

분류기(`classify.py`)가 읽는 코퍼스는 `60-data/corpus.json` (JSON 배열, 범용 스키마):

```json
[
  {
    "id": "<고유 id>",
    "title": "논문 제목",
    "abstract": "초록 전문",
    "keywords": "선택 — 세미콜론/공백 구분 키워드",
    "url": "선택 — 원문 링크",
    "flags": { "oral": false, "spotlight": false }
  }
]
```

- **필수**: `id`, `title`, `abstract`. **선택**: `keywords`, `url`, `flags`.
- `flags.oral`/`flags.spotlight`가 true면 쇼트리스트에서 우선 정렬된다.
- 학회 코퍼스 매핑 예: `id=poster_id`, `url=논문 페이지`, `flags.oral=oral 여부`. (ICML 예시는
  플러그인 `examples/icml2026-worked-example.md` 및 `references/phase_contracts.md`.)

수집 방법은 도메인마다 다르다(학회 크롤링·arXiv API 등) — 어떤 방법이든 이 스키마로 매핑해 두면
분류기·검수기가 그대로 동작한다. 코퍼스는 읽기 전용으로 다룬다.

## wiki 노트 스키마 (검색·승격 레이어 — LLM-wiki 운영 규칙 반영)

wiki 검색·승격 도구(`wiki_index.py`·`wiki_query.py`·`wiki_promote.py`)가 읽고 쓰는 정본 노트는
`20-knowledge-base/wiki/notes/<id>.md`. 스키마(gbrain·knowledge-manager 증류 규칙 A2·A3 반영):

```markdown
---
id: <노트 id>                 # 필수(A3) — 파일 stem과 일치, 위키링크 [[id]] 대상.
                              #   YYYYMMDDHHmm(zettel) 또는 kebab-slug 권장
title: <노트 제목>            # 필수(A3) — 노트 1개 = 아이디어 1개(원자성)
created: YYYY-MM-DD           # 필수(A3) — ISO 날짜
tags: [tag1, tag2]            # 필수(A3) — 3~5개 권장·소문자+하이픈·계층은 슬래시(ai/llm) (A5)
source: <출처 인용>           # 출처(B8) — 예: "arXiv:2401.00001, Table 1, p.6"
type: atomic                  # 선택 — atomic|moc|literature|permanent
---
## Compiled Truth

항상 "현재 확정 내용"만 담는다 — 새 증거가 오면 이 섹션을 통째로 REWRITE 한다 (A2).
각 수치·주장 옆에 페이지/표 인용 (예: "Entity F1 39.11 (Table 1, p.6)").
관련 노트는 위키링크로 연결하고 연결 이유를 한 줄 적는다 (A6) — 예: [[other-note]] (같은 기법 비교).

## Timeline

- YYYY-MM-DD 무엇이 확인/갱신됐는지 한 줄 (append-only — 기존 항목 수정·삭제 절대 금지, A2·E1)
```

- **lint 게이트(`wiki_promote`)가 강제하는 것**: A3 필수키(`id`·`title`·`created`·`tags`) +
  B8 출처 인용(source 프론트매터 또는 본문 페이지/표/arXiv/DOI/URL) + A2 2분할 구조
  (`## Compiled Truth` → `## Timeline` 순서). 미충족 시 승격 거부.
- **갱신 규칙(B5·E1)**: 기존 노트 갱신 시 Compiled Truth는 교체(REWRITE), Timeline은 append만 —
  기존 Timeline 항목의 수정·삭제가 감지되면 승격이 거부된다.
- **dedup(B4)**: 같은 id는 갱신, 다른 id·같은 제목은 거부(갱신이면 기존 id로, 신규면 제목 구분).
- frontmatter는 정규식 파서로 읽는다(단일값·인라인 리스트 `[a, b]`만 — 중첩 dict 미지원·pyyaml 불요).
- 검색 리포트는 `20-knowledge-base/wiki/queries/`에 저장되며 재생성 가능하다(사람이 편집하지 않음).
- 링크 그래프: `wiki_index`가 매 색인마다 본문 `[[..]]`를 정규식으로 추출해 `.index/edges.json`에
  기록하고(B6 — zero-LLM), orphan·broken link를 감사 리포트로 남긴다(D2).
