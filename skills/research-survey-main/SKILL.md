---
name: research-survey-main
description: This skill runs the end-to-end research survey tutorial and orchestration. Use when a user wants to survey papers for a research topic, organize a literature review, or learn/run the survey pipeline. Example triggers — "/research-survey", "연구 서베이 해줘", "논문 서베이 튜토리얼", "관심 주제 논문 정리", "ICML 논문 모아서 정리", "research survey", "paper survey tutorial", "리서치 토픽 추적", "서베이 파이프라인 돌려줘".
---

# research-survey-main — 서베이 튜토리얼 오케스트레이터

정본 대본은 `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/references/RUNBOOK.md` 하나다.
이 스킬은 그 대본을 읽고 **라이브로 진행**하는 얇은 진입점이다(어댑터 층 — RUNBOOK이 SOT).

## 발동 시 즉시 (문서 출력이 목적이 아니다 — 진행하라)

1. `RUNBOOK.md`를 읽는다. §0 인트로 스크립트로 시작한다(인사 → 오늘 배울 것 한 줄 → 목차 →
   첫 사례 제안). **각 단계는 반드시 질문으로 끝낸다**(자기-계속 암시 금지).
2. 사용자 언어를 감지해(한/영) 그 언어로 진행한다.
3. 대화형 선택(모드·주제·카테고리)은 **AskUserQuestion 툴 JSON**으로 묻는다 — 텍스트 질문 금지.
4. 3개 모드 라우팅:
   - **show(시연·기본)**: 한 카테고리를 "맨몸 LLM 요약 vs 근거 추적 서베이"로 통쏘기 대조.
     마무리에 `assets/templates/summary_comparison.html`을 슬롯 치환해 자립형 대조표 1장 생성.
   - **build(구축)**: `research-survey-init`으로 워크스페이스를 만들고 `research-survey-run`으로
     한 사이클을 실제로 돌린다(추출→요약→검증→정리).
   - **explore(탐색)**: 사용자의 즉석 질문을 taxonomy 다이얼로 매칭해 관련 논문을 찾아 보여준다.

## 파이프라인 요약 (상세는 references)

```
[다이얼] taxonomy 정의/조정 (관심 주제)  → references/taxonomy_dial.md
   ▼
[추출]  결정론 분류 (다중라벨·랭킹)
   ▼
[선별]  쇼트리스트(상위 N)
   ▼
[요약]  논문별 PDF 실측 요약 (Summary 4절·Why·Evidence 페이지인용·source_pdf)
   ▼
[검증]  ★3중: 자가검증 → 독립 실측 → 표본 PDF 대조 (producer≠evaluator)
   ▼
[정리]  Notion/wiki 축적 + 인사이트 추출
   ▼
[가설]  아이디어 → idea-critic 채점(reviewer+inspector) → accept/hold → ledger
   ▼
[지속]  arXiv 데일리 매칭 → 다이제스트
```

## 참조 문서 (references/)
- `RUNBOOK.md` — ★정본 대본(분 단위 진행표·용어 글로서리·단계 배너·안전핀)
- `phase_contracts.md` — 11단계 각각의 입력/처리/출력/게이트 계약
- `taxonomy_dial.md` — 관심 주제를 다이얼로 정의·조정하는 법(patterns/relevance/noise/threshold)
- `quality_gates.md` — 5대 원칙·3중검증·cold-read·콘텐츠 무결성 규칙·accept_threshold
- `roles.md` — 다중 노드 협업 시 역할(master·worker·reviewer·inspector·cso)과 통신
- `citation_rules.md` — 출처·삼각검증·품질등급·source_pdf 대조 규칙

## 자산 (assets/)
- `templates/taxonomy.template.json` — 다이얼 시작 템플릿
- `templates/survey_section.md` — 서베이 산출 섹션 템플릿
- `templates/summary_comparison.html` — 자립형 대조표(슬롯 치환)
- `templates/workspace/` — workspace-standards 준수 예시 워크스페이스 스캐폴드

## 안전핀 (읽기 전용·오염 방지)
- 참고 코퍼스/원본 repo는 읽기 전용. 산출물은 사용자 워크스페이스에만 쓴다.
- 정본(wiki) 직접 쓰기 금지 — 승격 게이트 경유. 외부 발행(git push·메시지 발송)은 사용자 승인.
