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
