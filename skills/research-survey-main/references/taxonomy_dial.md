# taxonomy_dial — 관심 주제를 다이얼로 정의·조정하는 법

> **핵심 사상**: 서치스페이스(무엇을 모을지)는 **단일 파일 `taxonomy.json` 하나**로 지배한다.
> 넓히기·좁히기·제외·새 주제 추가가 전부 이 파일 편집 → 재실행 → diff 보고로 끝난다.
> 같은 다이얼이 **학회 스냅샷 추출**과 **arXiv 신착 매칭**을 동시에 지배한다(스냅샷 ↔ 흐름).

## 다이얼 구조

```json
{
  "title_weight": 3,
  "default_threshold": 3,
  "guards": {
    "lm":  "\\b(LLMs?|large language models?|...)\\b",
    "vlm": "\\b(VLMs?|vision[- ]language|...)\\b",
    "med": "\\b(medical|clinical|CT scans?|X-?rays?|CXR|...)\\b"
  },
  "categories": {
    "<카테고리명>": {
      "desc": "한 줄 정의 (사람용)",
      "guard": "lm",              // 이 정규식이 문서 전체에 1회↑ 매칭돼야 후보
      "threshold": 3,            // score 이 값 이상이면 채택
      "patterns": [ "..." ],     // recall 축 — 매칭 시 가점(title 히트 = title_weight)
      "relevance_terms": [ "..." ], // +1 부스트 (핵심 어휘)
      "noise_terms": [ "..." ],  // -2 강등 (무관 응용어)
      "exclude": [ "..." ]       // 매칭 시 문서 단위 배제(하드)
    }
  }
}
```

## 4개 손잡이

| 하고 싶은 것 | 만지는 곳 | 효과 |
|---|---|---|
| **넓히기(recall↑)** | `patterns` 추가 · `threshold`↓ · `guard` 완화/null | 후보 증가 |
| **좁히기(precision↑)** | `relevance_terms`(+1) · `noise_terms`(−2) · `threshold`↑ | 저관련 강등·cut |
| **하드 제외** | `exclude` 정규식 | 문서 단위 완전 배제 |
| **새 관심축** | `categories`에 새 항목(desc/guard/threshold/patterns) | 새 카테고리(스냅샷+흐름 동시 상속) |

## 점수 규칙 (결정론)
- 각 pattern이 **제목**에 매칭 → `+title_weight`, **초록/키워드**에 매칭 → `+1`.
- 각 relevance_term 매칭 → `+1`. 각 noise_term 매칭 → `−2`.
- `guard` 미매칭 문서는 후보에서 제외(카테고리 전제). `exclude` 매칭 문서도 제외.
- 최종 score ≥ threshold 면 채택. **다중 라벨 허용**(한 논문이 여러 카테고리에 속할 수 있음).

## 정규식 주의 (실측)
- 인라인 플래그 `(?i)`를 패턴에 넣지 말 것 — 분류기가 IGNORECASE로 컴파일. 넣으면 "global flags
  not at the start" 에러.
- guard가 너무 넓으면(예: "patients?" 하나로 medical) 비의료 유입 → relevance/noise·threshold로 조인다.

## 조정 운영 규약 (1–2일 단위)
1. 다이얼 편집 → 재분류 실행 → `summary.md` 카운트 **diff**와 **표본 5편**을 보고.
2. 조정 사유를 카테고리 `desc`나 커밋 메시지에 1줄 남긴다.
3. 표본 검수는 고정 시드(`--sample <cat> N`)로 재현 가능하게.
4. 정제된 텀은 지속 서베이(arXiv) 토픽에도 미러링해 흐름에 동일 적용.

## 튜닝 예시 (worked example에서)
- `medical-data-gen` 최초 `guard: med`가 "patients?/diseases?"까지 포함 → 59편(비의료 혼입) →
  guard를 실제 의료영상/EHR 어휘로 조이고 noise_terms(protein·genomic 등) 추가 → **29편**으로 정밀화.
- `data-synthesis`가 고전 비전 데이터증강까지 잡음 → `guard: lm` 부여 → 44편 → 19편.
