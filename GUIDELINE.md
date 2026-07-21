# GUIDELINE.md — research-survey 워크스페이스 세미나 발표자료 생성 사양

> **용도**: 이 문서를 소스로 세미나 PPT(슬라이드 아웃라인 + 슬라이드별 구어체 발표 스크립트)를 생성한다.
> 이 문서 자체는 발표자료가 아니라 **발표자료를 만들기 위한 지시서/사양**이다.
> **수치 사용 절대 규칙**: 발표에 들어가는 모든 수치·사례는 §4 실증 수치표에 명기된 것만 쓴다(전건 실측·출처 병기).
> 여기 없는 수치가 필요하면 지어내지 말고 "측정 예정"으로 말한다. 과장 금지 — "여러 AI가 서로 감시·반박하며 걸러내고, 최종 판단은 사람이 한다"는 신중한 톤.

## 1. 발표 개요

- **주제**: "리서치 검수 하네스 — 근거가 추적되는 연구 서베이 워크스페이스" (research-survey 플러그인 v0.6.x)
- **청중**: AI 스터디원(비전문가 포함) — 전문용어는 나올 때마다 한 줄 풀이
- **시간**: 15~20분 + 실습 데모
- **핵심 메시지**: ①"맨몸 LLM 요약"과 "근거 추적 서베이"는 전혀 다른 결과를 낸다 ②검수는 만든 자가 아니라 **결정론 채점기와 다른 벤더의 눈**이 한다 ③이 시스템은 그 차이를 **재실행 가능한 수치**로 측정한다
- **정체성 한 줄(메타하네스 프레임)**: "연구를 대신 해주는 도구가 아니라, **검증 가능한 연구 하네스를 찍어내고 그 하네스의 품질까지 측정하는 메타하네스**" — workspace-standards 하네스 4단계(basic/runtime-ready/runtime-enforced/meta-harness) 기준 **meta-harness 성질**: init이 측정기(gold·매설·채점기)를 내장한 워크스페이스를 생성하고, team-compare로 하네스 구성(팀 벤더 조합)의 검수 품질까지 실험한다. 정직한 경계 2가지 — ①승격 강제는 hook(runtime-enforced)이 아니라 `wiki_promote.py` **스크립트의 결정론 게이트**(dry-run→apply·exit 1)로 구현된다(이 플러그인은 hook 0건) ②채점 결과→규칙 자동 재조정 루프는 미구현(사람 승인 경유) — 향후 방향.

## 2. 서사 아크 (슬라이드 흐름의 뼈대)

1. **후크(문제)**: AI 결과물은 "그럴듯하게 틀린다" — 할루시네이션 3유형(거짓/오출처·누락·부실)
2. **답(설계)**: 파이프라인 — taxonomy 다이얼 → 결정론 추출 → PDF 실측 요약 → 3중 검증 → **wiki 승격 게이트** → 지속 서베이
3. **차별점(왜 다른가)**: 승격 게이트를 코드로 강제(위치 경계·출처 lint·Timeline 불변·dedup) / 노트 2분할(Compiled Truth·Timeline) / 검색 = FTS5+bigram BM25의 RRF 융합 / 링크·엣지는 zero-LLM(환각 0) — gbrain·knowledge-manager·wiki-demo의 검증된 패턴 이식
4. **실증(핵심)**: §4 수치표 — 채점 하네스가 성능을 수치로 증명 + **교차 벤더 리뷰가 단일 벤더 미탐 결함을 잡은 실사례 3건**(§5)
5. **실습**: `/research-survey demo`(6단계 체험) + `team-compare` 랩(팀 구성별 할루시네이션 검출 차이 실험)
6. **로드맵·마무리**: P2(리랭커·MOC·상태 머신)·P3(vector·GraphRAG·자율 정비) — "도구가 아니라 검수 문화"

## 3. 시스템 상세 (설계 슬라이드용 사실)

- **배포**: Claude Code 플러그인(공개 repo `HanEol-Lee77/research-survey`·마켓플레이스 원격 설치)·python stdlib만(의존성 0)
- **구성**: `/research-survey` 라우터(tutorial·init·run·demo·team-compare) + 스킬 3종 + scripts 8종(wiki 4: index/query/promote/grade · corpus 2: classify/fetch · verify 1 · team 1)
- **워크스페이스**: 10단위 넘버링·CLAUDE.md 12섹션(workspace-standards 준수)·60-data 샘플 코퍼스 15편(관련 7 arXiv verbatim + 무관 8)
- **검수 층**: promote 게이트(A3 필수키·B8 출처·E1 Timeline 불변) + source-coverage(수치·인용구 원문 실재 — 퍼센트·소수·정수 전부, 좌표 마스킹·경계 매칭) + 3중 검증 계약
- **평가 하네스**: gold 질문 12 + 매설 오류 노트 5종 + clean 대조군 1 → `wiki_grade.py`가 적중률·거부율·과차단을 결정론 채점

## 4. 실증 수치표 (★발표에 쓸 수 있는 유일한 수치 — 전건 실측)

| 수치 | 값 | 출처 |
|---|---|---|
| retrieval 1위 적중 / top-5 recall | **12/12 (100%) / 100%** | wiki_grade E2E(v0.5.0 게이트·3자 독립 재현: worker·리뷰어 2종) |
| 매설 오류 거부율 | **5/5 (100%)** — 층별 분리(promote 3·coverage 2) | 동일 |
| clean 대조군 | **통과 1/1·과차단 0·미판정 0** | 동일 |
| coverage 편입 효과 | 매설 거부 **3/5 → 5/5** (source-coverage 층 추가로) | v0.5.0 통합 재채점 |
| 샘플 코퍼스 무결성 | 15편 arXiv API 대조 **15/15 verbatim** | v0.3.0 R2 재대조 |
| classify 분리 | 관련 재현율 7/7·무관 오탐 0/8 | v0.3.0 증보2 실측 |
| 신규 사용자 완주 | 데모 전 단계 PASS·자기 주제 반입 사이클 완결 | FIELD_TEST_REPORT_v040 (T2·T3) |
| 개발 검증 규모 | 릴리스 게이트 전건 수렴 — v0.2.x~v0.5.0 5회 실측(이후 버전은 CHANGELOG 참조)·리뷰 라운드 12회+ | 라운드 장부 |

## 5. 교차 벤더 리뷰 실증 사례 (실습 랩의 동기 — 발표의 백미)

이 플러그인 **개발 과정 자체**에서, 한 벤더 리뷰어가 놓친 결함을 다른 벤더가 잡은 실사례:

| # | 결함 | 놓친 쪽 → 잡은 쪽 | 성격 |
|---|---|---|---|
| 1 | 채점 하네스의 gold 무결성 우회(빈 근거=통과) + 발명 정수 미탐 | Claude 리뷰어 ACCEPT → **codex(gpt-5.5)가 적대 재현으로 2건 적발** (v0.5.0 R1) | 검수기 자체의 구멍 |
| 2 | 승격 게이트가 workspace 밖 파일도 정본에 씀(경로 미검증) | 동일 라운드 Claude ACCEPT → **codex 적대 재현으로 적발** (v0.3.0 R1) | 게이트 우회 |
| 3 | npm .CMD 심이 개행 프롬프트를 첫 줄에서 절단 — codex 방향 검수가 "지적 0건"으로 위장 무효 | 최초 "모델 성향" 오진 → **Claude 리뷰어가 판별 실험 2회로 원인 입증** (v0.6.0 R1) | 위장 무결(silent failure) |
| 공통 교훈 | "문서 코드 블록은 눈으로 읽지 말고 실행 실측하라" / 단일 벤더 구성엔 상관 사각지대가 실재한다 | 양방향(사례 1·2는 gpt가 Claude 미탐을, 사례 3은 Claude가 gpt 레그 결함을 잡음) | |

> 전사(前史·정확한 귀속): PowerShell `"$c:"` 파싱 오류(v0.2.1)는 네이티브 codex가 아직 없던 시기, **같은 벤더(Claude) 안의 교차 렌즈 리뷰어**가 2라운드 미탐을 "실행 실측"으로 깬 사례다 — 벤더가 아니라 방법론이 잡았고, 이 사건이 "코드 블록 실행 실측" 교훈과 네이티브 교차 벤더 복원의 계기가 됐다(출처: v0.2.1 CHANGELOG의 reviewer-2 = Claude 폴백).

→ **team-compare 랩**은 이 경험을 누구나 재현하는 실험으로 상품화한 것: producer/reviewer를 서로 다른 LLM으로 조합(예: codex gpt-5.6-sol × Claude(Fable/Opus), 역조합)해 동일 입력·동일 결정론 채점기로 검출 차이를 측정한다. 판정은 LLM 자평이 아니라 채점기만 한다.

## 6. 실습 시나리오 (데모 슬라이드·라이브용)

1. `/plugin marketplace add HanEol-Lee77/research-survey` → install → `/research-survey demo`
2. demo 6단계: 스캐폴드 → 샘플 자동 복사 → classify(관련 7편 추출) → wiki 검색(DEER 질문 → 1위 정답·근거 발췌) → **검수 거부 시연 2종**(출처 없는 산출물·Timeline 변조 → exit 1) → 정상 승격·재검색
3. 품질 채점: `wiki_grade.py` → 적중률·거부율 실시간 산출
4. 자기 주제 전환: `corpus_fetch --query "<내 주제>"` → 다이얼 수정 → classify → 노트 작성·승격
5. team-compare 랩: dry-run(비용 미리보기) → 2팀 실행 → 비교 리포트
6. **커리큘럼 트랙**(단계별 학습 경로): `/research-survey curriculum` → 4주 과정(week01 일단
   돌아가게 → week02 지식 창고+검수 기준 → week03 하네스 견고화+Loop → week04 멀티에이전트
   심의)으로 위 1~5 데모를 스터디 정본 4주 커리큘럼에 매핑해 진행 상황 실측 기반으로 안내
- **라이브 실패 대비**: FIELD_TEST_REPORT·데모 E2E 캡처를 사전 캡처로 준비, "지금은 미리 돌려둔 결과로 보겠습니다"라고 정직하게 전환(라이브 실패를 숨기지 않는다)

## 7. 발표 산출물 생성 지시 (이 문서를 프롬프트로 쓸 때)

- 산출: ①슬라이드 아웃라인 15~20장(장별 제목·핵심 불릿·시각 요소 제안) ②장별 구어체 발표 스크립트(존댓말·전문용어 한 줄 풀이·단계 사이 질문 종료) ③백업 Q&A 5문항
- 형식 규칙: LaTeX 수식 금지·토큰 수치는 맥락 문장으로·모델 조롱 톤 금지("모델 탓이 아니라 구조 한계")
- 검증: 생성 후 모든 수치를 §4·§5 표와 대조(불일치=수정), 출처 없는 주장 0 확인 — grounded-deck 방식의 독립 검증 패스 권장

## 8. 소스 자료 경로 (심화 참조)

- 이 repo: README.md(개요)·skills/research-survey-main/references/{RUNBOOK.md, TEAM_COMPARE.md, DEMO.md}·CHANGELOG.md(릴리스 이력)
- 분석·리포트(pack round/): COMPARATIVE_ANALYSIS_v040.md(3대 리포 비교)·FIELD_TEST_REPORT_v040.md(필드 테스트)·LLM_WIKI_RULES_DISTILLED.md(gbrain·km 규칙 증류)
- 스터디 정본: improve_wiki/gpters23_intro/0_PLAN_STUDY_.md(스터디 프레임·할루시네이션 3유형·4주 커리큘럼)
