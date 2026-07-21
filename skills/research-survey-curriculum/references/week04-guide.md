# Week 04 — 멀티에이전트 심의 + 발표

> 스터디 정본 4주차("멀티에이전트 소크라테스 심의 + 평가·리뷰 시스템 + 운영 루프")를 매핑.
> 목표: 교차 벤더(서로 다른 LLM) 팀으로 producer/reviewer를 구성해 단일 모델이 놓친 오류를
> 잡고, 그 실증을 GUIDELINE로 Before/After 발표 자료로 정리한다.

## 이번 주 목표
- 같은 논문을 팀별로 (producer 요약 → reviewer 검수) 나란히 돌려 "누가 만들고 누가 봤는지"에
  따라 잡히는 결함이 달라지는 걸 본다(교차 벤더 리뷰).
- 판정·집계는 여전히 **결정론 채점기**가 한다는 원칙(결정성 경계)을 끝까지 지킨다.
- 개발 중 실제로 "교차 벤더가 단일 벤더 미탐 major를 잡은 사례"를 발표 자료로 정리한다.

## 지금 할 일

### 1. 팀 정의 (실측 가용 CLI만)
- `00-system/teams.json`(샘플 `teams.sample.json`): 팀별 `producer`/`reviewer`의 cli·
  cmd_template·model. **이 머신에 실제로 있는 CLI만** 넣는다(없는 CLI는 실행기가 fail-closed로
  막는다). 역조합 2팀(A: X가 만들고 Y가 검수 / B: Y가 만들고 X가 검수)이 교차 벤더 대비의 핵심.

### 2. 비용 미리보기 → 실행 (team-compare)
- 진입: `/research-survey team-compare` (정본 절차는 플러그인 `references/TEAM_COMPARE.md`).
- 기본이 **dry-run**이다 — 실 LLM 호출 0, 예상 호출 수(팀×논문×2)만 보여준다. 확인 후에만
  `--yes`로 실행한다(비용 가드). 프롬프트는 stdin으로 전달된다(개행 절단 회피).
- 팀별 분리 작업영역(`40-drafts/<team_id>/`)에 producer 요약·reviewer 검수(JSON)가 남는다.

### 3. 결과 읽기 (결정성 경계 유지)
- 리포트(`80-reports/team-compare-report.md`): 팀별 **Evidence 실재율(수치·직접인용)·coverage
  FAIL·reviewer 지적·매설 검출률**. 판정·집계는 결정론 채점기(`verify_summaries`)가 한다 —
  LLM 자평을 점수 근거로 쓰지 않는다.
- ★정직 읽기: 'Evidence 실재율'은 수치·직접인용 substring 실재만 본다(질적 허위는 범위 밖).
  needle 수가 적으면 **low-evidence**로 표시되니 100%를 근거 충실로 과신하지 말고 reviewer
  지적·본문 정독과 병행 해석한다. reviewer가 **비수신·비응답**이면 지적 0건이 아니라
  **unchecked(검수 불능)**로 구분된다(위장 무결 차단).

### 4. 발표 준비 (GUIDELINE)
- 발표 자료 사양은 `GUIDELINE.md`(세미나 발표자료 생성 사양). §4 수치표·§5 교차 벤더 실증
  사례 3건(개발 중 실제로 codex↔Claude 상호 검수가 단일 벤더 미탐을 잡은 기록)·실습 시나리오를
  활용한다. Before/After(1주차 손 검수 vs 4주차 하네스 자동 대조)를 한 줄로 정리한다.
- 정직 경계: 이 시스템은 "메타하네스"(검증 가능한 연구 하네스를 찍어내고 그 품질까지 측정)를
  지향하되, 채점 결과 → 규칙 자동 재조정 루프는 미구현(사람 승인 경유)임을 GUIDELINE이 명시한다.

## 완료 체크리스트
- [ ] `teams.json`을 실측 가용 CLI로 역조합 2팀(교차 벤더)으로 정의했다.
- [ ] `/research-survey team-compare` dry-run으로 예상 호출 수를 먼저 확인했다.
- [ ] `--yes`로 실행해 팀별 producer 요약·reviewer 검수·비교 리포트를 받았다.
- [ ] 리포트를 정직하게 읽었다(low-evidence·unchecked 구분·질적 허위는 범위 밖 인지).
- [ ] 개발 중 교차 벤더 실증 사례(GUIDELINE §5)를 발표 자료로 정리했다.
- [ ] Before/After 한 줄: "1주차 대비 검수 시간·적발력이 ___만큼 달라졌어요."

## 이번 주 산출물
- 멀티에이전트(교차 벤더) 심의 데모 · 팀 비교 리포트 · Before/After 발표 자료 · 4주 회고 한 줄.

## 마무리
4주 커리큘럼 완주 — 내 도메인의 검증 가능한 검수 하네스를 갖췄습니다. 이후에는 30일 감사·
Open Questions 환류·지속 서베이(`corpus_fetch --since --append`)로 운영 루프를 돌리면 됩니다.
`/research-survey help`로 전체 커맨드를 다시 볼 수 있어요. 수고하셨습니다.
