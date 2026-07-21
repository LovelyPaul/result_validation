# Week 03 — 하네스 견고화 + Loop

> 스터디 정본 3주차("흔들리지 않는 Agent Harness 3기둥 + Loop Engineering")를 매핑.
> 목표: 결정론 게이트 체계를 세우고, 중단·재개(run_state)와 30일 감사·Open Questions 환류로
> "시간이 지나도 흐려지지 않는" 하네스를 만든다. 같은 결과물을 여러 번 채점해 재현을 확인한다.

## 이번 주 목표
- 결정론 게이트(승격 lint·source-coverage·gold/매설 채점)를 하나의 체계로 묶어 "통과"를 증명한다.
- 파이프라인이 중단돼도 누락 없이 재개되게 상태를 기록한다(run_state).
- 위키가 낡지 않게 30일 감사(stale·MOC 제안·Open Questions)를 운영 절차로 삼는다.
- 같은 결과물을 여러 번 채점해 판정이 재현되는지 확인하고, 미해소 질문을 다음 사이클로 되먹인다.

## 3기둥 매핑 (스터디 3기둥 ↔ research-survey 실기능)

| 스터디 기둥 | research-survey 실구현 |
|---|---|
| ① 결정론 검증 게이트 | `wiki_promote` lint(B8·E1·A3·위치) + `verify_summaries --corpus`(인용 실재·커버율) + `wiki_grade`(적중률·거부율) — 전부 스크립트 출력으로만 판정 |
| ② 독립 외부모델 리뷰 루프 | week04의 `team_compare`(producer≠reviewer 교차 벤더) — 3기둥 중 이 축은 4주차에 본격화 |
| ③ 결정성 경계 | 모델은 후보만, **임계·집계·정지 판정은 스크립트**(예: `wiki_grade --min-top1/--min-reject`, run_state의 done 판정) |

## 지금 할 일

### 1. 결정론 게이트를 "채 치기"로 반복
- week02에서 만든 게이트(승격 lint → source-coverage → gold/매설 채점)를 한 라운드로 보고,
  **같은 결과물을 여러 번** 돌려 판정이 재현되는지 확인한다. 채점에 **최소 적중률·최소
  거부율 임계**를 걸면 게이트가 된다 — 미달이면 실패(exit 1)로 막힌다. 이 채점·임계 게이트는
  **research-survey-run 스킬이 실행한다**(사용자가 내부 스크립트를 직접 부르지 않는다). gold
  무결성 위반(기대 근거 문구가 노트에 없음)은 임계와 무관하게 실패다 — 채점 기준 자체의 오염 차단.

### 2. 중단·재개 (run_state)
- 긴 사이클은 단계 상태를 `_meta/run-state.json`에 남긴다 — 단계는
  `extract→shortlist→summarize→verify→organize→delta`. 상태 파일은 **코드 상수 기준으로
  검증**되어(변조·누락·부정 상태·stale 재개 포인터는 fail-closed) 신뢰할 수 있다.
- 재시작·중단 후에는 **재개 포인터(첫 비-done 단계)부터** 이어간다 — 이미 done인 단계는
  다시 돌리지 않는다(중복 작업·비용 방지). 진행 상황은 상태 파일을 직접 읽어 파악한다.

### 3. 30일 감사 + Open Questions 환류
- 위키는 쌓기만 하면 낡는다. **30일마다(또는 대량 승격 직후)** 감사를 돌려 건강도를 본다
  (research-survey-run 스킬의 `wiki_index --audit`):
  - orphan(연결 0)·broken link·**stale**(updated/created 30일 초과)·**contrasts 쌍**(모순
    관계)·**MOC 제안**(동일 태그 5+ 노트에 MOC 부재 시 제안·자동 생성 안 함)·**미해소
    Open Questions** + 건강도 카운트 1줄.
- 노트 frontmatter `open_questions: [질문1, 질문2]`에 미해소 질문을 적어 두면, 감사가 이를
  집계해 **다음 사이클의 다이얼/선별 시드**로 재투입한다 — 검증된 위키가 스스로 다음 조사
  방향을 지목하는 순환(Loop). 산출물의 인사이트를 일회성으로 버리지 않는다.

## 완료 체크리스트
- [ ] 같은 결과물을 3번 채점해 판정(적중률·거부율)이 **재현**되는 걸 확인했다.
- [ ] `--min-top1/--min-reject` 임계를 걸어 게이트가 exit 1로 미달을 막는 걸 봤다.
- [ ] `run_state`로 사이클 단계를 기록하고, 중단 후 재개 포인터부터 이어가는 흐름을 확인했다.
- [ ] `wiki_index --audit`로 stale·MOC 제안·Open Questions·건강도를 점검했다.
- [ ] 노트에 `open_questions`를 적고, 감사가 그것을 다음 시드로 집계하는 걸 확인했다(Loop 1회).
- [ ] 하네스가 잡아낸 근거 없는 주장·조작 수치 **1건을 캡처**하고 한 줄 코멘트를 남겼다.

## 이번 주 산출물
- 결정론 재현 테스트(같은 판정 3회) · run-state 중단·재개 기록 · 30일 감사 리포트(건강도) ·
  Open Questions 환류 1회 · 적발 케이스 1건 이상 + 코멘트.

## 다음 주
week04 — 교차 벤더 멀티에이전트 심의(team-compare)로 단일 모델이 놓친 오류를 잡고, GUIDELINE로
Before/After 발표를 준비한다. `/research-survey curriculum week04`. 다음으로 넘어갈까요?
