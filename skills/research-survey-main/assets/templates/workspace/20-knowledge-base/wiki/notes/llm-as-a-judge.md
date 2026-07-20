---
id: llm-as-a-judge
title: LLM-as-a-Judge — MT-Bench·Chatbot Arena 검증
created: 2026-07-20
tags: [llm-as-judge, evaluation, human-preference]
source: arXiv:2306.05685
---
## Compiled Truth

강한 LLM을 심판(judge)으로 써서 개방형 질문에 대한 챗 어시스턴트를 평가하는 접근의 사용법과
한계를 검증했다 (arXiv:2306.05685 abstract).
- 확인된 편향: **position·verbosity·self-enhancement 편향**과 제한된 추론 능력 — 일부 완화책 제안 (abstract).
- 검증 벤치마크 2종: MT-bench(멀티턴 질문 세트)·Chatbot Arena(크라우드소스 배틀) (abstract).
- 결과: GPT-4급 심판은 통제·크라우드 인간 선호와 **80% 이상 일치** — 인간끼리의 일치 수준과 같음.
  LLM-as-a-judge는 인간 선호의 확장 가능하고 설명 가능한 근사다 (abstract).

관련: [[deer-benchmark]] (rubric 기반 평가로 확장), [[selfcheckgpt]] (판정 전 검출 게이트)

## Timeline

- 2026-07-20 초기 승격 — arXiv export API 초록 실측 기반 작성 (arXiv:2306.05685)
