---
name: research-survey-run
description: This skill runs one full survey cycle for a category — extract, summarize, triple-verify, organize. Use when a user wants to actually execute a survey pass on a topic/category. Example triggers — "/research-survey run", "이 카테고리 서베이 돌려줘", "논문 추출해서 요약·검증까지", "서베이 한 사이클 실행", "run survey cycle", "카테고리 정리해줘".
---

# research-survey-run — 한 카테고리 서베이 1사이클

지정 카테고리를 **추출 → 선별 → 요약 → 3중 검증 → 정리**까지 한 바퀴 돌린다.
단계 계약은 `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-main/references/phase_contracts.md`,
검증 규칙은 `quality_gates.md`, 인용 규칙은 `citation_rules.md`를 따른다.

## 도구 (플러그인 동봉 · 자립형 · python3 표준 라이브러리)
- 분류: `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/classify.py`
- 검수: `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/verify_summaries.py`
- 입력 규약: `<ws>/00-system/taxonomy.json` + `<ws>/60-data/corpus.json`(범용 스키마 —
  `00-system/data-dictionary.md`: id/title/abstract/keywords?/url?/flags?). 코퍼스가 학회 원본이면
  먼저 이 스키마로 매핑해 `60-data/corpus.json`을 만든다. 출력은 `<ws>/70-analysis/`.

## 발동 시 즉시 (문서 출력이 아니라 실행)

1. 대상 카테고리·워크스페이스를 확인(모호하면 AskUserQuestion 툴 JSON). 코퍼스는 `60-data/corpus.json`,
   다이얼은 `00-system/taxonomy.json`. corpus.json이 없으면 도메인 소스를 범용 스키마로 매핑해 만든다.
2. **[추출]** 동봉 분류기로 결정론 분류 → 카테고리 편수·랭킹:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/classify.py" --workspace <ws>
   python "${CLAUDE_PLUGIN_ROOT}/.../classify.py" --workspace <ws> --sample <cat> 14   # 표본 검수(고정 시드)
   ```
   정밀도 부족이면 다이얼 조정(relevance/noise/threshold) 후 재실행 — before/after 편수 diff 보고.
3. **[선별]** 쇼트리스트 상위 N(oral/중요도 우선).
4. **[요약]** 논문별로 요약 작성 — **논문 1편당 서브에이전트 1개** 병렬(PDF 전문 실측). 규격:
   Summary(문제/방법/핵심결과/한계) · Why(연구 접점) · Evidence(수치 + `— Table X, p.Y`) ·
   `source_pdf: <파일> (p.1 제목 대조 OK)`. **착수 전 PDF p.1 제목 ↔ 목록 제목 대조**(불일치=플래그).
   → 산출은 워크스페이스 `40-drafts/<cat>/`.
5. **[검증 — 3중]** ①자가검증: `verify_summaries.py --dir <ws>/40-drafts/<cat>` (플레이스홀더 0·
   섹션·페이지인용≥3·source_pdf) ②독립 실측: 다른 세션/서브에이전트가 같은 스크립트 재실행 ③표본
   원문 대조: 카테고리당 2편 cold-read PDF 대조. 상충 시 원문 실측 최종심.
6. **[정리]** 검증 통과분을 `50-output/`·`80-reports/`에 정리(요약 인덱스 + 인사이트). 목적지가
   Notion이면 툴 제한(문단·표 크기) 대응해 업로드하고 API로 카운트 대조. **일괄 조작은 명시 ID만**.
7. **[증분]** `80-reports/`의 서베이 문서에 이번 배치를 Delta Log로 append(전체 재작성 금지).
   `CHANGELOG.md`·`PROJECT_STATUS.md` 갱신.

## 상태 추적 · 중단·재개 (agy#11 — 파이프라인 상태 머신)
장기 사이클은 중단·에러로 끊길 수 있다. 단계 상태를 `_meta/run-state.json`에 남겨 **누락 없이
재개**한다(결정론 — LLM 판단 아님). 단계: extract→shortlist→summarize→verify→organize→delta.
- **사이클 시작 시 1회**: 상태 파일 초기화(전 단계 pending).
  ```
  python "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/run_state.py" --workspace <ws> init --category <cat>
  ```
- **각 단계 착수/완료마다**: 상태 갱신(진행 중·완료·실패 + 사유 note).
  ```
  python "${CLAUDE_PLUGIN_ROOT}/.../run_state.py" --workspace <ws> mark summarize in_progress
  python "${CLAUDE_PLUGIN_ROOT}/.../run_state.py" --workspace <ws> mark summarize done
  ```
- **세션 재시작·중단 복구 시**: `... show`로 재개 포인터(첫 비-done 단계)를 확인하고 **거기부터**
  이어간다 — 이미 done인 단계는 다시 돌리지 않는다(중복 작업·비용 방지).
  ```
  python "${CLAUDE_PLUGIN_ROOT}/.../run_state.py" --workspace <ws> show
  ```

## 완료 게이트
- 3중 검증 전건 PASS · 정리 산출물 존재 · Delta Log 갱신 · run-state 전 단계 done(재개 포인터
  = 전건 완료). 각 단계는 질문으로 종료(다음 진행 확인).

## 가설로 이어가기 (선택)
- 인사이트의 갭에서 가설을 만들려면 `research-survey-main`의 §가설 절차(idea-critic 채점 → accept/hold
  → ledger)로. hold는 딥다이브(근거 논문 전문 정독)로 재구성.
