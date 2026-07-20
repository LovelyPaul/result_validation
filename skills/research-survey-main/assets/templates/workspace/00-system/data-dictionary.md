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

## wiki 노트 스키마 (검색·승격 레이어)

wiki 검색·승격 도구(`wiki_index.py`·`wiki_query.py`·`wiki_promote.py`)가 읽고 쓰는 정본 노트는
`20-knowledge-base/wiki/notes/<id>.md`, frontmatter 스키마는 다음과 같다:

```markdown
---
id: <kebab-case-id>          # 필수 — 파일 stem과 일치, 위키링크 [[id]] 대상
title: <노트 제목>            # 필수
tags: [tag1, tag2]           # 선택 — 인라인 리스트(공백 토큰 파싱, pyyaml 미사용)
source: <출처 인용>           # 필수 — 예: "arXiv:2401.00001, Table 1, p.6"
created: YYYY-MM-DD           # 선택
---
본문 (각 수치·주장 옆에 페이지/표 인용을 단다 — 예: "Entity F1 39.11 (Table 1, p.6)")
```

- **필수**: `id`, `title`, `source`. `wiki_promote`의 lint 게이트가 이 세 키와 출처 인용
  (source 프론트매터 또는 본문의 페이지/표/arXiv/DOI/URL 인용)을 강제한다 — 미충족 시 승격 거부.
- frontmatter는 정규식 파서로 읽는다(단일값·인라인 리스트 `[a, b]`만 — 중첩 dict 미지원).
- 검색 리포트는 `20-knowledge-base/wiki/queries/`에 저장되며 재생성 가능하다(사람이 편집하지 않음).
