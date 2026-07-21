---
title: TEAM_COMPARE (멀티 LLM 팀 구성 비교 실습 랩 정본)
version: 0.6.0
duration: 10-15분 (dry-run) + 실행 시 팀×논문×2 LLM 호출
role: 진행자가 이 대본대로 가이드 — 설치 후 워크스페이스에서 '교차 벤더 리뷰가 단일 벤더 미탐을 잡는다'를 바로 따라 하게 한다
---

# TEAM_COMPARE — 멀티 LLM 팀 구성 비교 실습 랩 (정본)

> `/research-survey team-compare`의 정본. 진행 톤·산출물 규약·안전핀은 RUNBOOK 정본을 따른다
> (각 단계 배너 + 질문 종료·LaTeX 금지·플러그인 폴더 쓰기 금지).

## 왜 이 랩인가 (동기 — 실증 사건)

이 플러그인을 개발하는 동안 **교차 벤더 리뷰**가 결정적이었다: 한 벤더가 만든 산출물을
**다른 벤더가 검수**하니, 만든 벤더 스스로는 놓쳤던 major 결함을 잡아냈다(단일 벤더로
producer·reviewer를 다 맡기면 같은 맹점을 공유해 미탐이 남는다 — "egoless review"가
성립하지 않는다). 이 랩은 그 구성을 **설치 직후 워크스페이스에서 바로 따라 해** 보게 한다.

핵심 원칙(RUNBOOK 품질 게이트와 동일): **판정·집계는 LLM이 아니라 결정론 채점기**가 한다.
producer 요약이 얼마나 근거에 충실한지는 `verify_summaries`의 source-coverage로 원문 대조해
수치로 매긴다 — LLM의 "잘한 것 같다"를 점수 근거로 쓰지 않는다(환각0·garbage-in 차단).

## 구성 요소

| 요소 | 파일 | 역할 |
|---|---|---|
| 팀 정의 | `00-system/teams.json` (샘플 `teams.sample.json`) | 팀별 producer/reviewer의 CLI·cmd_template·model. **실측 가용 CLI만**·교차 벤더 권장 |
| 실행기 | `team_compare.py` | 팀별 분리 작업영역 생성 → producer 요약 → reviewer 검수 → 결정론 채점 → 비교 리포트 |
| 채점 | `verify_summaries` 재사용 | 인용 실재율·coverage FAIL(발명·오인용)·(옵션)매설 검출률 |

## 진행 흐름 (각 단계 질문으로 종료)

**① 팀 정의 준비** — `▶ [1/4] 팀 — 누가 만들고 누가 검수할지 정합니다`
- `${CLAUDE_PLUGIN_ROOT}/.../assets/templates/workspace/00-system/teams.sample.json` →
  워크스페이스 `00-system/teams.json` 복사. 이 머신에 실제로 있는 CLI만 남긴다(§0.5 실측
  기준 — 없는 CLI를 넣으면 실행기가 '미설치' 진단으로 막는다). 역조합 2팀(A: X→Y 검수 /
  B: Y→X 검수)이 교차 벤더 대비의 핵심.

**② 비용 미리보기 (dry-run)** — `▶ [2/4] 미리보기 — 실 호출 수를 먼저 봅니다`
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/team_compare.py" --workspace . --ids <arxiv-id>
```
- 기본이 dry-run이다 — 실 LLM 호출 0. `[dry-run] 팀 N · 논문 M · 예상 실 LLM 호출 (N×M×2)회`와
  팀별 producer/reviewer를 출력한다. 비용·시간을 확인하고 진행 여부를 사용자에게 묻는다.

**③ 실행 (--yes)** — `▶ [3/4] 실행 — 팀별로 요약·검수를 돌립니다`
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/team_compare.py" --workspace . --ids <arxiv-id> --yes
```
- 팀별 분리 작업영역(`40-drafts/<team_id>/`)에 producer 요약(`<id>.md`)·reviewer 검수
  (`<id>.review.json`)를 남긴다. producer는 **초록만 근거** 지시를 받는다.
- 오류 매설 실험을 원하면 `--seeded <phrases.json>`({"phrases":[...]})로 매설 문구가 요약에
  유입됐는지·reviewer가 잡았는지 **매설 검출률**을 결정론으로 채점한다.

**④ 비교 리포트 읽기** — `▶ [4/4] 해석 — 어느 팀이 근거에 충실했나`
- `80-reports/team-compare-report.md`(+`.json`): 팀별 **인용 실재율·coverage FAIL·reviewer
  지적 건수·(옵션)매설 검출률** 표. 해석: 인용 실재율이 낮거나 coverage FAIL이 있는 producer는
  근거에서 벗어난 것이고, **교차 벤더 reviewer가 그것을 지적했는지**가 이 랩의 관전 포인트다.

## 해석 가이드 (무엇을 배우나)
- **단일 벤더 함정**: producer와 reviewer가 같은 벤더면 같은 맹점을 공유해 미탐이 남는다.
  역조합 2팀을 비교하면 "누가 만들고 누가 봤는지"에 따라 잡히는 결함이 달라지는 걸 본다.
- **결정론 채점의 역할**: LLM reviewer의 지적은 후보일 뿐, 최종 판정은 verify_summaries의
  원문 대조가 한다 — reviewer가 놓쳐도 coverage FAIL로 발명·오인용이 드러난다.
- 이 랩은 축소판이다. 실제 서베이에서는 RUNBOOK §6 3중 검증(producer≠evaluator)으로 확장된다.

## 실측 관찰 (개발 중 E2E 1회 — 2팀 역조합·논문 1편, 정직 기록)
개발 중 실 LLM E2E에서: **claude-producer 팀은 초록만 근거로 4절 요약을 정확히 생성**
(Evidence 인용 5건 전부 초록 verbatim·인용 실재율 100%·coverage FAIL 0). 반면 **codex-producer
팀은 요약 대신 "초록을 보내달라"는 비응답을 반환**(같은 프롬프트인데도 — CLI별 헤드리스
프롬프트 전달·모델 응답 성향 차이). 결정론 채점기는 이를 **거짓 통과시키지 않고** 인용 실재율
None(집계 불가)으로 표시했다 — 이 지점이 랩의 교훈이다: **어떤 팀 구성은 producer 단계에서
이미 실패하며, 그것을 LLM 자평이 아니라 결정론 채점이 드러낸다.** 팀 정의 시 각 CLI의
헤드리스 프롬프트 전달을 먼저 dry-run이 아닌 소규모 실행으로 확인하라.

## 안전핀 (RUNBOOK §4 준수)
- 기본 dry-run — 실 LLM 호출은 `--yes` 명시 시에만(비용 가드). 호출 수를 먼저 보여준다.
- 산출물은 워크스페이스 `40-drafts/<team_id>/`·`80-reports/`에만. 플러그인 폴더 쓰기 금지.
- teams.json에는 §0.5로 실측된 CLI만 — 없는 CLI는 실행기가 fail-closed로 막는다.
