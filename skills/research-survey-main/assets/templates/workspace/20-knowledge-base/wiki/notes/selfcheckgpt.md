---
id: selfcheckgpt
title: SelfCheckGPT — 제로 리소스 블랙박스 할루시네이션 검출
created: 2026-07-20
tags: [hallucination-detection, black-box, sampling]
source: arXiv:2303.08896
---
## Compiled Truth

SelfCheckGPT는 외부 데이터베이스 없이(zero-resource) 블랙박스 모델의 응답을 팩트체크하는
샘플링 기반 기법이다 (arXiv:2303.08896 abstract).
- 핵심 아이디어: 모델이 그 개념을 알면 샘플된 응답들이 서로 비슷하고 일관된 사실을 담지만,
  **할루시네이션이면 샘플들이 서로 갈라지고 모순**된다 (abstract).
- 검증 셋업: GPT-3로 WikiBio 인물 지문을 생성하고 사실성을 수동 주석 (abstract).
- 결과: 문장 수준 할루시네이션 검출 AUC-PR·지문 수준 사실성 상관 모두 grey-box 대비 높음 (abstract).

관련: [[deer-benchmark]] (평가 벤치마크 계열), [[llm-as-a-judge]] (판정자 관점)

## Timeline

- 2026-07-20 초기 승격 — arXiv export API 초록 실측 기반 작성 (arXiv:2303.08896)
