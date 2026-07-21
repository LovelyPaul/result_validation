---
id: deer-benchmark
title: DEER — 전문가 보고서 평가 벤치마크
created: 2026-07-20
tags: [llm-evaluation, deep-research, rubric]
source: arXiv:2512.17776
source_grade: api_summary
open_questions: [claim verification 아키텍처가 uncited 주장의 evidence quality를 실제로 얼마나 정확히 정량화하나, 101 rubric items가 도메인 밖 보고서에도 이식되나]
---
## Compiled Truth

DEER는 deep research 시스템이 만든 전문가급 보고서를 평가하는 벤치마크다 (arXiv:2512.17776 abstract).
- 평가 기준을 전문가 개발 taxonomy **7 dimensions·25 subdimensions**로 체계화하고, 이를
  **101개 fine-grained rubric items**로 운영화했다 (abstract).
- rubric 평가에 더해 **claim verification 아키텍처**를 제안 — cited·uncited 주장 모두 검증하고
  evidence quality를 정량화한다 (abstract).
- 실험 결과: 현 시스템들은 구조적으로 그럴듯하고 근거를 인용하는 보고서를 내지만, 전문가급
  요청 충족과 논리적 완결성에서 여전히 부족하다 (abstract).

관련: [[selfcheckgpt]] (검출 계열 — 보고서 단위 vs 문장 단위), [[llm-as-a-judge]] (LLM 심판의 한계 보완)

## Timeline

- 2026-07-20 초기 승격 — arXiv export API 초록 실측 기반 작성 (arXiv:2512.17776)
