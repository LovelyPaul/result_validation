# Changelog

All notable changes to this plugin are documented here (Keep a Changelog style).

## [0.7.0] - 2026-07-21

### Added (P2 5건 — COMPARATIVE_ANALYSIS P2 · gemini 2nd-wave #3·#5·#11 · km D4/D5 · codex#9, 오너 승인)
- **[1·agy#3] pseudo-reranker + 질의 라우팅** (`wiki_query.py`): RRF 상위 후보를 결정론 렉시컬
  겹침(제목·본문 문자 bigram 겹침·제목 가중)으로 **2단 재정렬**. 질의를 내용어 토큰 수로
  단순(≤2)/복합 분기 라우팅해 혼합비(rrf_mix)를 조정(단순=렉시컬↑·복합=RRF↑). 재정렬은
  RRF 상위 후보의 순서만 바꾼다(집합·dangling 불변). **gold 12문항 재채점 무회귀 실측**:
  1위 적중 12/12(100%)·top-5 recall 100% 유지. 라우팅·재정렬 self-test 추가.
- **[2·agy#5] MOC 자동 제안** (`wiki_index.py --audit`): 동일 태그 노트가 5개 이상인데 그
  태그의 MOC 노트(`type: moc`)가 없으면 제안(노트 목록·제안 파일명 `<태그>-MOC.md`).
  **제안만**(자동 생성 금지 — 조립은 사람). MOC 존재 시 제안 제외. self-test.
- **[3·agy#11] 파이프라인 상태 머신** (`run_state.py` 신규): run 사이클 단계(extract→shortlist→
  summarize→verify→organize→delta)를 `_meta/run-state.json`에 기록(단계 enum·완료 플래그·재개
  포인터). init/mark/show CLI·fail-closed(미지 단계·상태). research-survey-run SKILL에 중단·재개
  절차 추가. team_compare는 팀별 단계 상태(produce/review/grade)를 리포트에 기록. self-test.
- **[4·km D4/D5] Open Questions 환류**: 노트 frontmatter `open_questions`(선택) +
  `wiki_index --audit`가 미해소 질문 집계 출력 + RUNBOOK '다음 사이클 시드 재투입' 절.
  템플릿 노트 `deer-benchmark`에 예시 2건. self-test.
- **[5·codex#9] source_grade**: `corpus_fetch`가 레코드에 `source_grade`(api_summary)·
  `retrieved_at` 기록(순수 `stamp_retrieved_at`로 날짜 주입 테스트). 노트 frontmatter
  `source_grade` 선언 지원(`wiki_index` load) + `verify_summaries.check_grade_consistency`가
  요약↔원문 grade 불일치 시 경고(**verbatim 직접인용은 동일 grade만** — 다르면 특히 위험 명시).
  data-dictionary 스키마 갱신. self-test.

### Fixed (이월 minor)
- `team_compare._parse_review` 배열 envelope 정합: 단일 object를 감싼 1원소 배열
  `[{"flagged":[...]}]`은 언랩해 검수 인정, 2원소+ 배열·비object는 unchecked(R2 엄격성 유지).
  docstring을 실제 동작과 정합화. self-test.

### Verified (P2)
- self-test 8종 전건 PASS·exit0: wiki_index·wiki_query·wiki_promote·corpus_fetch·verify_summaries·
  wiki_grade·team_compare·run_state(신규). gold 재채점 무회귀(12/12·100%)·데모 코어 E2E 무파손·
  `claude plugin validate` exit0.

### Fixed (P2 R1 — reviewer-codex REVISE major 1, 적대 재현 수용)
- **(major) `run_state.py` persisted state 스키마 검증**: `load()`가 디스크 상태를 검증 없이
  신뢰하고 `mark()`가 디스크의 stage 이름을 허용 목록으로 삼아, 변조된 run-state.json의
  unknown stage(`evil`)·부정 status(`banana`)·누락/중복 stages·stale resume를 show/mark가
  승인·재작성하던 구멍(codex 재현). `_validate()`가 **코드 상수 STAGES·STATUSES 기준**으로
  ①stage 집합·순서 일치(누락·unknown·중복·순서 뒤섞임 일괄) ②status enum ③stale resume를
  검사해 위반 시 fail-closed(`SystemExit '상태 파일 스키마 위반: ...'`). `mark()`도 상수 대조로
  unknown stage 거부. `init_state`의 stages 파라미터 제거(고정 스키마). self-test 5케이스
  (unknown/부정/누락/중복/stale) + 정상 통과·mark 상수 거부 회귀.

### Changed
- `plugin.json`·RUNBOOK·DEMO frontmatter version 0.7.0. README 2종 Scripts 그룹표에 state 행 추가.
- GUIDELINE.md 메타하네스 프레임 정체성 1항 동승(master 작성·정정 — runtime-enforced를
  wiki_promote 스크립트 게이트로 정직화·하네스 4단계 정합).

## [0.6.0] - 2026-07-21

### Changed (P0 — repo 구조 개편, RESTRUCTURE_PLAN.md 옵션1 승인·집행)
- **문서 정돈**: `INSTALL_MARKETPLACE.md` → `docs/`, `PRIVATE_REPO_SETUP.md` → `docs/archive/`
  (공개 전환으로 용도 소멸 — 비가역 삭제 대신 아카이브 이동·`git mv`로 이력 보존·아카이브
  배너 1줄 추가). 링크 참조 전수 스캔: 실참조는 CHANGELOG(이력·불변)뿐·라이브 링크 0.
- **scripts 기능군 논리 구획**: 7종 각 상단에 `[기능군: wiki|corpus|verify]` docstring 헤더
  1줄 부여(동작 무변경). 물리 위치는 유지 — 상호 import 결합(wiki_query→wiki_index,
  wiki_grade→wiki_query/wiki_promote/verify_summaries)이 co-location에 의존하기 때문.
  물리 분리(옵션2)는 차기 메이저 재검토 항목으로 RESTRUCTURE_PLAN §6에 보존.
- **README 2종**: 기여자용 "Scripts" 그룹표 추가(wiki/corpus/verify + v0.6.0 team 예약 행).
- **개편 매핑**: INSTALL_MARKETPLACE.md→docs/INSTALL_MARKETPLACE.md ·
  PRIVATE_REPO_SETUP.md→docs/archive/PRIVATE_REPO_SETUP.md.
### Verified (P0)
- self-test 6종 전건 PASS·exit0(헤더 주석이 sys.path 형제 import 무손상 실증) · 데모 코어
  E2E(classify 7편→index 3노트→query 1위 deer-benchmark) · grade E2E(적중 12/12·거부 5/5·
  exit0) · `claude plugin validate` exit0.

### Added (P1 — team-compare 멀티 LLM 팀 비교 실습 랩)
- **`team_compare.py`** (scripts/·stdlib): 같은 논문을 팀별로 (producer 헤드리스 요약 →
  reviewer 검수)한 뒤 **판정·집계는 결정론 채점기만**(verify_summaries의 resolve_source·
  check_evidence_grounding 재사용 — 인용 실재율·coverage FAIL·옵션 `--seeded` 매설 검출률).
  팀별 분리 작업영역(`40-drafts/<team_id>/`)·비교 리포트(`80-reports/team-compare-report.{md,json}`).
  **비용 가드**: 기본 dry-run(실 LLM 호출 0·호출 수 미리보기)·`--yes`로만 실행.
  실주행 버그 4종 회피(review-workspaces 실측): ①Windows .ps1 npm shim은 shutil.which 해소 후
  powershell 라우팅 ②프롬프트 argv 리스트(shell=False)로 인용 붕괴 회피 ③stdin=DEVNULL hang 방지
  ④codex --skip-git-repo-check trusted-dir 회피. self-test는 CLI 호출 0(fake runner 주입).
- **`teams.sample.json`** (00-system/): 팀 정의 스키마(team_id·producer/reviewer의 cli·
  cmd_template·model). 실측 가용 조합만(codex↔claude 역조합 2팀)·미설치 CLI는 주석 예시.
- **정본 `references/TEAM_COMPARE.md`**: 동기(교차 벤더 리뷰가 단일 벤더 미탐 major를 잡은
  실증)·구성·해석 가이드. `/research-survey team-compare` 커맨드 라우팅·RUNBOOK §3 포인터.

### Changed
- `plugin.json`·RUNBOOK·DEMO frontmatter version 0.6.0.

### Fixed (P1 R1 — claude-1 REVISE major 1 + minor 2)
- **(major) team_compare 프롬프트 전달 argv→stdin**: Windows npm `.CMD` 심이 개행 포함 argv를
  **첫 개행에서 절단**해 producer가 프롬프트 첫 줄만 받고 비응답하던 원인 규명·수정
  (1차 E2E에서 codex-producer가 "초록 달라"로 응답한 진짜 원인 — 모델 성향 차이 아님).
  프롬프트를 stdin으로 전달(`subprocess.run(input=prompt)`) — codex exec·claude -p 모두 수용.
  심 라우팅은 `_wrap_shim`으로 분리: `.ps1`→`powershell -File`(.ps1 전용)·`.cmd`/`.bat`→`cmd /c`
  (powershell -File은 .ps1만 받아 `.CMD`를 넣으면 실패 — R1 재실행에서 실측 후 교정)·`.exe`는 그대로.
- **(major 연동 1b) reviewer 비수신·비응답 unchecked 구분**: `_parse_review`가 `{"flagged":[...]}`
  JSON을 실제 받았을 때만 checked=True. 비JSON·flagged 키 부재는 **unchecked(검수 불능)**로
  구분해 리포트 표기 — 지적 0건('무결')으로 위장 집계하지 않는다(위장 무결 차단).
- **(minor) TEAM_COMPARE.md 실측 관찰 정정**: '모델 응답 성향 차이' → Windows 심 절단 버그
  (규명·수정됨)로 원인 교정.
- **(minor) teams.sample _examples 라벨·리포트 표기 정정**: '미설치 CLI' → 실측 가용(gemini·
  ollama·agy) 반영·stdin 전달 주의 명시. 리포트의 인용 실재율 None은 빈 셀 대신
  '집계 불가(Evidence needle 0)'로 표기.
- self-test 추가: 개행 프롬프트 stdin 전문 도달(절단 회귀 방지)·reviewer 비응답→unchecked·
  `_parse_review` checked/unchecked 판별.

### Fixed (P1 R2 — reviewer-codex REVISE major 3, 적대 probe 재현·전건 수용)
- **(major) `_parse_review` 스키마 엄격화**: flagged 키 존재만 보던 것 → root가 object이고
  flagged가 **list이며 모든 원소가 비어있지 않은 string**일 때만 checked=True. `{"flagged":null}`
  (→[]·checked 위장), `{"flagged":"ABC"}`(문자별 리스트로 허위 지적 건수) 등 schema-invalid
  JSON이 unchecked 게이트를 우회하던 구멍 봉쇄. self-test 7타입(null·string·number·object·
  혼합·빈문자열·비object root) + 유효 대조군.
- **(major) team_id·paper id 경로 위생**: `_safe_id`(영숫자 시작+영숫자·._- 만·`..`·구분자·
  절대경로 거부)로 검증 + `_ensure_within`(resolve 후 허용 root 하위 `is_relative_to` fail-closed).
  `team_id='../../outside-team'`·`paper id='../../../outside-paper'`가 workspace 밖에 파일을 쓰던
  것(codex containment probe 재현) 차단. 중복 team_id도 실행 전 거부. arXiv id의 점(2303.08896)은
  허용. self-test: 이탈 2케이스·중복·정상 id.
- **(major) 지표 범위 정직화**: '인용 실재율' → **'Evidence 수치·직접인용 substring 실재율'**로
  리포트·문서 라벨 한정. needle(검증 가능 성분) 수 < 임계(기본 3)면 **low-evidence 플래그**
  표기(실재 인용 1개+허위 qualitative Summary 조합이 100%로 과신되던 우회를 드러냄).
  TEAM_COMPARE.md에 '지표 범위·한계' 절 신설(질적 주장은 검증 안 함·reviewer 검수/본문 정독
  병행 해석). self-test: qualitative 반례가 low-evidence로 잡히고 리포트에 경고 표기됨.

## [0.5.0] - 2026-07-21

### Added (비교 분석 P1 5건 — gbrain·knowledge-manager·wiki-demo 대조 격차 해소, 오너 승인)
- **P1-1 retrieval·검수 평가 하네스 `wiki_grade.py`** (최대 격차 — wiki-demo의 gold+매설
  패턴 이식): ①gold 질문셋(`00-system/wiki-gold.json` — 질문·기대 1위 노트 id·기대 근거
  문구) 일괄 실행 → **1위 적중률·top-k recall** 산출. 랭킹은 `wiki_query.query()`를 그대로
  호출(채점기≠검색기 이중 구현 금지). ②gold 무결성 fail-closed: 기대 근거 문구가 기대 노트
  본문에 실재하는지 검사 — 위반 시 exit 1(채점 기준 오염 차단). ③오류 매설 노트
  (`40-drafts/ev/*.md`)를 검수 게이트 체인(promote lint dry-run → source-coverage)에 넣어
  **거부율** 산출 — dry-run만 사용(정본·manifest 무변조), 판정은 rejected/passed/unchecked
  3어휘(원문 해결 불가는 unchecked 명시 — 조용한 통과 금지). source-coverage 층은
  `verify_summaries`의 `resolve_source`·`check_evidence_grounding`을 재사용. ④JSON 리포트
  (`70-analysis/wiki-grade-report.json`) + `--min-top1`/`--min-reject` 임계 게이트(미달 exit 1).
  동봉 샘플: **gold 12문항**(근거 문구 전건 노트 원문 대조 실측) + **매설 5종**(발명 수치·
  문구 오인용·출처 없음·Timeline 변조·필수키 누락 — 발명 수치 94.2와 오인용 문구가 실제
  arXiv 초록에 부재함을 실측 확인). DEMO ⑦ 품질 채점(선택)·RUNBOOK 품질 채점 절·
  data-dictionary 채점 데이터 스키마 문서화.
- **P1-2 source-coverage 검수** (`verify_summaries.py --corpus [--source-dir]
  [--coverage-threshold]`): ①Evidence 인용 실재 — Evidence 절의 수치(퍼센트·소수·정수 —
  기본 구현은 정수 보수 제외였고 같은 릴리스 R1에서 마스킹+스코프로 정수까지 확장, 아래
  Fixed R1)와 인용 문구(12자+)가 원문에 substring 실재하는지 grep 대조,
  부재=FAIL(발명 수치·오인용 차단). 원문은 `--source-dir`의 PDF 추출 .txt 우선, 없으면
  corpus abstract(+제목). **원문 미해결(arXiv id 표기 없음·corpus 미등재)=FAIL**(fail-closed —
  조용한 검사 생략은 매설 우회 루프홀). ②키포인트 커버율 — 초록을 문장 단위 키포인트로
  쪼개 내용어 40%+ 공유 시 커버, 커버율 < 임계(기본 0.6)면 WARN(exit 불반영 — 한글 완전
  의역의 저평가 가능성은 결정론 근사 한계로 문서화). `--corpus` 미지정 시 기존 동작 그대로
  (하위호환)·self-test 신설.
- **P1-3 stale 감지 + 감사 정식화** (`wiki_index.py --audit`): frontmatter `updated`(없으면
  `created`) 나이 **30일 초과 stale 목록**(날짜 파싱 불가는 fail-closed로 stale 포함·
  age_days=None)·**건강도 1줄**(notes/edges/orphan/broken/stale/skipped — 일반 색인 실행에도
  출력)·`--audit` 상세 리포트(stale·contrasts 쌍·confidence 선언). manifest에 audit.stale·
  health 기록. RUNBOOK에 30일 주기 감사 운영 절차 절(후속 조치 포함).
- **P1-4 타입드 엣지 + confidence 최소형**: `[[id|rel]]` 구문 파싱 — rel∈contrasts/supports/
  extends는 관계 타입, 별칭·무파이프는 기본 `links` → `edges.json`에 rel 기록(dedup은
  (src,dst,rel)). audit에 **contrasts 쌍 목록**(상충 연구 모순 가시화). 노트 frontmatter
  `confidence` 선언(직접 인용 1.0/요약 추출 0.7)을 manifest `note_confidence`에 기록(float
  불가 선언은 원문 보존 — 조용한 폐기 금지). **검색 랭킹 보정은 이번 범위 제외** — RUNBOOK
  로드맵에 후보로만 명시.
- **P1-5 arXiv 델타 지속 서베이** (`corpus_fetch.py --since YYYY-MM-DD`): 제출일(published)
  필터 — `--query`/`--ids` 어느 쪽과도 조합, `--append` 병용 시 "지난 반입 이후 신규분만
  병합"(델타 반입). 응답 rows에 `published` 키 추가(Atom published 파싱), published 결측·
  불량 항목은 **fail-closed 제외+경고**, `--query`+`--since`는 submittedDate 최신순 정렬
  요청(--max 창이 신규분을 향하게), `--since` 형식 오류는 명시 SystemExit. RUNBOOK §2.5에
  지속 서베이 절 신설 — phase_contracts §11(지속 서베이)의 실행화.

### Fixed (이월 minor 2건)
- `corpus_fetch` 연결층 오류 명시 진단: URLError(오프라인·DNS·연결 거부)·TimeoutError(60s)를
  raw traceback 대신 SystemExit 진단으로 교체(HTTPError 백오프 경로와 분리) + 모의 opener
  self-test.
- DEMO frontmatter version 0.5.0 동기화(0.4.0에 머물러 있던 것).

### Fixed (R1 — reviewer-codex REVISE 2건 + claude-1 minor 2건, master 전건 수용)
- **(codex) `wiki_grade` gold 무결성 빈 문자열 루프홀**: expected_evidence가 누락·빈 문자열·
  공백만이면 `'' in body`가 항상 True라 무결성 검사를 조용히 통과하던 구멍(리뷰어 재현) —
  strip 후 비어 있으면 'in body' 검사 전에 위반으로 카운트. 공백만 evidence self-test 회귀
  케이스 + CLI 부정 프로브(빈 evidence gold → exit 1) 실측.
- **(codex) `verify_summaries` 발명 정수 미탐지**: 정수 전면 제외가 '999 datasets'류 발명
  정수를 놓치던 것 — 정수 포함 전수 검사로 확장하되 오탐은 컨텍스트 창이 아니라
  **마스킹+스코프**로 회피(인용 좌표 p.N/Table/Figure/§/Section/arXiv id/날짜 마스킹·행머리
  목차 번호 마스킹·연도형 4자리 제외·숫자 경계 매칭으로 999↔1999 오매칭 차단·소형 정수
  ≤12는 영어 수사(seven 등) 표기 인정). 단위 self-test 5건 추가.
- **(claude-1 minor) clean 대조군 동봉**: `40-drafts/ev/ev-clean-control.md` — 모든 수치·
  인용이 원문 초록에 실재하는 정상 노트(`ev_expect: pass` 선언). 게이트가 통과시켜야
  정상 — **과차단(overblocked) 감시**. wiki_grade가 expected/as_expected를 판정·거부율
  분모는 매설(expected=reject)만으로 유지(대조군 혼입에 의한 수치 희석 방지).
- **(claude-1 minor) DEMO 인트로 단계 번호 정합**: 인트로의 개념 나열 번호(⑤품질 채점)가
  본문 단계 번호(⑦)와 어긋나던 것 — 인트로가 본문 단계 번호(③④⑤⑥⑦)를 직접 참조하도록 수정.

### Verified
- self-test 6종 전건 PASS·exit 0: wiki_index(fts5_available=True)·wiki_query·wiki_promote·
  corpus_fetch·verify_summaries(신설)·wiki_grade(신설). R1 반영 후 재실행 전건 PASS 유지.
- grade E2E(격리 워크스페이스·동봉 샘플, R1 재채점): **retrieval 1위 적중 12/12(100%)·top-5
  recall 100%·gold 무결성 위반 0 / 매설 거부 5/5(100%)·clean 대조군 1/1 통과·과차단 0·
  미판정 0(정확 분리)** — promote 층 3건(출처 없음 B8·Timeline 변조 E1·필수키 누락 A3) +
  source-coverage 층 2건(발명 수치 '94.2' 원문 부재·오인용 문구 원문 부재).
  `--min-top1 0.9 --min-reject 0.9` 게이트 exit 0. 빈 evidence gold 부정 프로브 exit 1.
- 데모 코어 E2E 실완주: classify 7편(오탐 0) → query 1위 deer-benchmark → 타입드 엣지 포함
  노트 승격(dry-run diff → apply → manifest 기록) → 델타 재색인(+1·supports 엣지 rel 기록·
  confidence 0.7 note_confidence 기록·건강도 1줄) → 재검색 1위 = 방금 승격 노트.
- `claude plugin validate` exit 0.

## [0.4.1] - 2026-07-21
### Fixed (필드 테스트 F2~F7 — v0.4.0 발행본 신규 사용자 시나리오 실측 후속)
- **(F2) `corpus_fetch` HTTP 오류 처리**: HTTPError가 raw traceback으로 노출되던 것을 명시
  진단(상태코드·안내)으로 교체. 429/503(일시 rate-limit — 필드 실측)은 45s 백오프 후 **1회**
  재시도, 그래도 실패하면 SystemExit. 모의 opener self-test 3케이스(백오프 성공·재실패·404).
- (F3·F4·F5) `INSTALL_MARKETPLACE.md`에 "설치 문제 해결" 절 신설: clone 타임아웃=비공개 repo
  404 가능성·로컬 add 폴백 / update는 `name@marketplace` 형식 필요 / Windows EBUSY 재시도.
- (F6) DEMO ①에 수동 진행 시 최소 필요 폴더 4종 명시.
- (F7) RUNBOOK §2.5에 다중라벨 편수 동반 변동 설명(카테고리 추가 시 기존 카테고리 편수도
  변할 수 있음 — 정상 동작) 1줄.

## [0.4.0] - 2026-07-20
### Added
- **`/research-survey demo`** — toy 실행 워크플로우(설치 직후 5~10분 자동 체험). 정본
  `references/DEMO.md`: ①워크스페이스 스캐폴드(대상 폴더 AskUserQuestion) ②샘플 코퍼스·
  taxonomy·**위키 노트 3개** 자동 복사 ③classify 실행(관련 7편 추출 화면) ④wiki_index→
  wiki_query 검색 시연(DEER 질문 → 근거 발췌) ⑤검수 거부 시연 2종(출처 없는 산출물 B8 거부·
  Timeline 변조 E1 거부) ⑥정상 승격 dry-run→apply+manifest. 커맨드 라우팅 표에 demo 추가.
- **샘플 위키 노트 3개 동봉**(템플릿 `20-knowledge-base/wiki/notes/`): deer-benchmark·
  selfcheckgpt·llm-as-a-judge — 검증된 arXiv 초록만 근거로 작성(2분할·필수키·arXiv 출처 인용),
  전건 promote lint 통과 실측. 설치 직후 검색 시연이 바로 되는 근거 데이터.
- **`corpus_fetch.py`** (scripts/·stdlib only): arXiv export API로 `--ids` 또는 `--query --max`
  → 범용 스키마 corpus.json 생성(제목·초록 API 원문 verbatim). `--append`는 기존 코퍼스 병합
  (중복 id 스킵). `--self-test`는 네트워크 0(fixture 파싱·병합 검증). "누구나 원하는 논문을
  가져올 수 있게"의 실행 경로.
- **RUNBOOK §2.5 "자기 주제로 바꾸기"**: 다이얼 수정 + corpus_fetch 반입 + classify 재실행 흐름.
### Fixed (R2 이월 minor 2건)
- `wiki_query` RRF 루프에 채널 내 중복 id 방어(seen per channel) — stale db 대비 1회만 누산.
- CHANGELOG [0.3.0]의 promote lint 필수키 문구를 최종 기준(`id/title/created/tags`)으로 교정.
### Verified
- 데모 E2E 실완주(임시 워크스페이스): ②복사→③classify 7편→④index 3노트·엣지 6·감사 클린,
  query 1위 deer-benchmark→⑤B8 거부·E1 거부(각 exit 1·정본 미생성)→⑥dry-run·apply exit 0·
  manifest 기록→승격 노트 재색인(델타 +1)·재검색 1위 확인.
- 격리 CLAUDE_CONFIG_DIR 마켓플레이스 설치 실측: `marketplace add`(로컬 경로)✔ → `install`✔
  (1회 EBUSY 후 재시도 성공 — Windows 파일 잠금 일시 현상) → `plugin list` enabled ✔.

## [0.3.0] - 2026-07-20
### Added
- **wiki 검색·승격 레이어 실구현** — 지금까지 계약(phase_contracts §7·§9)만 있고 실행 도구가
  없던 갭을 메운다. `skills/research-survey-run/scripts/`에 자립형 스크립트 3종 추가(전부 python3
  표준 라이브러리·pyyaml 미사용·frontmatter 정규식 파싱·각 `--self-test` 내장):
  - `wiki_index.py` — `20-knowledge-base/wiki/notes/*.md`를 검색 색인으로 빌드. FTS5 가용성을
    이 머신 python에서 실측(`CREATE VIRTUAL TABLE ... USING fts5`) — 가용하면 SQLite FTS5
    가상테이블(id/title/tags/body), 불가하면 순수 파이썬 문자 bigram BM25 단독 폴백. mode를
    manifest.json·stdout에 명시. (실측 환경: sqlite 3.50.4 → FTS5 가용.)
  - `wiki_query.py` — 질문 → FTS5 매치 채널(`bm25()` 랭킹) + 문자 bigram BM25 랭킹 채널을
    **RRF(K=60)로 융합**한 top-k → `wiki/queries/`에 근거 발췌 리포트. 존재 노트만 위키링크
    (dangling 0 불변식). (시계열: 기본 구현(8c4550c)은 단순 유니온이었고 같은 릴리스 증보
    (80e6162)에서 RRF로 교체 — 최종 코드는 RRF. 아래 증보 절 참조.)
    **BM25 수식·전처리(K1=1.2·B=0.75·`_BM25_STRIP`·`_bigrams`·idf·score·(-score,id) 정렬)는
    tax-wiki 데모 `wiki/scripts/query.py`에서 그대로 이식** — ablation 검증 수식·임의 개선 금지.
  - `wiki_promote.py` — 검증 통과 산출물(40-drafts·80-reports)을 wiki 정본으로 승격하는 게이트.
    기본 dry-run(diff 미리보기), `--apply`는 승인 후에만. 노트 스키마 lint(frontmatter 필수키
    `id/title/created/tags` + 출처 인용 존재 — 최종 A3 확장 기준·아래 증보 절)를 코드로 강제해
    "정본 직접 쓰기 금지" 계약을 집행,
    승격 이력을 `wiki/promotion-manifest.jsonl`에 append.
- **워크스페이스 템플릿 고도화**: `20-knowledge-base/wiki/{notes,queries}/` 스캐폴드(.gitkeep+README),
  `00-system/data-dictionary.md`에 wiki 노트 frontmatter 스키마 추가, 템플릿 `CLAUDE.md` §10
  도구(결정론)에 wiki 3스크립트 사용법 추가.
### Added (증보 — LLM-wiki 운영 규칙 반영, gbrain·knowledge-manager 증류 [즉시] 항목)
- **A2 페이지 2분할 노트 스키마**: 노트 = `## Compiled Truth`(항상 현재값 — 갱신 시 통째
  REWRITE) + `## Timeline`(append-only). `wiki_promote` lint가 2분할 구조를 강제하고,
  **A3 frontmatter 필수키**를 `id/title/created/tags`로 확장(+B8 출처 인용 필수 유지).
  data-dictionary에 스키마·태그 규칙(A5)·링크 규칙(A6) 문서화.
- **`wiki_promote` 게이트 강화**: B4 dedup(같은 id=갱신, 다른 id·같은 제목=거부),
  B5 갱신 병합(Compiled Truth 교체 + Timeline append), E1 Timeline 불변(기존 항목 수정·삭제
  감지 시 승격 거부).
- **`wiki_index` 링크 그래프**: B6 zero-LLM 링크 추출(정규식 `[[..]]` → `.index/edges.json`
  엣지 테이블, src·dst·exists·extracted_at) + D2 감사(orphan·broken link 리포트) +
  C4 델타 색인(노트 sha256 대조 — 변경분만 FTS5 행 갱신, 무변경 시 재색인 생략).
- **`wiki_query` RRF 융합(C1)**: FTS5·bigram BM25 두 채널을 단순 유니온에서
  **Reciprocal Rank Fusion(K=60)**으로 교체 — 결정론·(-score,id) 정렬. BM25 수식 자체는 불변.
- **RUNBOOK wiki 운영 원칙**: brain-first(C3 — 외부 검색 전 위키 먼저)·컴파일 단계 분리(B1)·
  추측 금지(E5) 명시.
### Added (증보 2 — 샘플 research topic 코퍼스·다이얼 동봉)
- **`60-data/corpus.sample.json`** (템플릿 워크스페이스): 15편 — 스터디 주제 "리서치 검수
  하네스(할루시네이션을 잡는 평가·리뷰 하네스)" 관련 7편(DEER 2512.17776·CRITIC 2305.11738·
  SelfCheckGPT 2303.08896·LLM-as-a-Judge 2306.05685·ChatEval 2308.07201·G-Eval 2303.16634·
  Siren's Song 서베이 2309.01219 — **전건 arXiv 페이지 실측 검증, 제목·초록 verbatim**) +
  무관 8편(VLM 토큰압축·병리 MLLM 등 — 실측 코퍼스 papers.jsonl에서 verbatim 복사·발명 0).
- **`00-system/taxonomy.sample.json`**: 해당 주제 1카테고리 다이얼(threshold 4·guard lm·
  노이즈=토큰압축/KV-cache/멀티모달). **결정론 실증**: classify.py 실행 실측 — 관련 7/7 분류
  (재현율 100%)·무관 8편 오탐 0. RUNBOOK 환경 전제의 "코퍼스가 없으면" 경로를 이 샘플 복사
  실데이터 진행으로 갱신(낭독 모드는 보조).
### Fixed (리뷰어 R1 — reviewer-codex 독립 검수 major 3·minor 1, master 전건 수용)
- **(major) 승격 입력 위치 게이트**: `wiki_promote`가 src 위치를 검증하지 않아 workspace 밖
  임의 markdown도 `--apply`로 정본에 들어가던 구멍(리뷰어 실재현) — src가 workspace 하위이고
  첫 디렉터리가 `40-drafts`/`80-reports`일 때만 승격, 위반 시 rejected. outside-src·허용 외
  폴더 self-test 2건 추가.
- **(major) 샘플 코퍼스 verbatim 정합**: 2306.05685·2308.07201·2303.16634 세 편의 abstract가
  arXiv abs 페이지의 "this https URL" 링크 텍스트 잔재로 export API 원문과 불일치 — API
  summary 원문으로 교체(실 GitHub URL 복원). 교체 후 15편 전건 API 재대조: title·abstract
  15/15 일치 실측.
- **(major) 중복 노트 id fail-closed**: 색인/검색층이 duplicate frontmatter id를 조용히 1건으로
  붕괴시키던 결함(리뷰어 실재현) — `wiki_index`·`wiki_query`의 load_notes가 중복 발견 시
  SystemExit로 차단, id↔파일 stem 불일치는 감사 리포트(`audit.id_stem_mismatch`)에 포함.
  dup-id 거부 self-test 2건 추가.
- (minor) 이 CHANGELOG 상단 `wiki_query` 서술의 "유니온 top-k"를 RRF 융합으로 정정(시계열 명시).
### Design (로드맵 — 문서 기재만·v0.3.0 미구현)
- vector 임베딩 채널·시맨틱 캐시·토큰 예산 하드캡·GraphRAG(2-hop 라우팅)·cron 자율 정비·
  엣지 confidence decay — stdlib 플러그인 범위 밖, RUNBOOK §3 "향후 확장"에 명시.
### Changed
- RUNBOOK [정리·지속] 단계·§3 확장 모듈을 wiki 실도구 흐름으로 갱신(계약 → 실행 가능).
- `phase_contracts.md` §7(정리)·§9(승격)를 실도구(wiki_index/query/promote) 참조로 갱신.
- README 2종(영·한) Features·동작 원리에 wiki 검색·승격 레이어 반영.
- `plugin.json`·RUNBOOK frontmatter version 0.3.0.

## [0.2.1] - 2026-07-20
### Fixed (리뷰어 R1 수렴 지적 — 2종 REVISE 통합)
- **RUNBOOK §3.5 예외 신설**: 현재 작업 폴더가 플러그인 폴더 자체(clone 루트)인 세션은 거기에
  `artifacts/`를 만들지 않는다 — AskUserQuestion으로 산출 위치(사용자 폴더)를 물어 지정.
- **맨몸 요약 지시문 원문 명문화**(§0.5): "웹 검색·파일·도구 접근 없이, 이미 알고 있는
  학습지식만으로 답하세요. 모르는 내용은 모른다고 답하세요" 지시문을 placeholder 없이 수록.
  피험체 실행 cwd = 플러그인 폴더 밖 빈 폴더(bash/PowerShell 생성 명령 병기). 도구차단
  플래그는 실존 확인분만 기재 — claude `--tools ""`(모든 내장 도구 비활성, help 실측).
  codex·gemini·ollama는 전체 차단 플래그 미확인이라 지시문 문구+빈 cwd로 통제함을 명시.
- **AGENTS.md 변형 오프닝 정밀화**: ①즉답이 RUNBOOK 선독보다 우선(우선순위 명문화)
  ②특정 PDF·파일 첨부/지정 요약 요청은 변형 오프닝 아님(정상 처리) ③과거 답 재사용 시
  "같은 세션의 과거 답"임을 청중에 고지.
- **workspace-standards 참조 자립화**: RUNBOOK 환경 전제·init SKILL.md의 경로 인용 옆에
  핵심 요지 인라인(10단위 요지·12섹션 전체 목록·7-layer 한 줄) — 표준 리포 없이 이해 가능.
- **§0.5 PowerShell 블록 보강**: OS 실측 출력(`[System.Environment]::OSVersion`),
  python 폴백(`Get-Command` 선확인 → `py -3 --version`).
- §0.5 선택지 예시에 gemini 추가. 7-layer 인용을 §8.1(7-layer)/§8.2(강도 4단계)로 통일
  (RUNBOOK·init SKILL·CHANGELOG 0.2.0 항목).
- **README 2종 사용 모드 명시**: 마켓플레이스 설치(루트 어댑터 미로드 — command/skill 사용)
  vs clone+cd(어댑터 유효 — 변형 오프닝 동작) 구분 안내.
### Fixed (리뷰어 R2 잔여 — reviewer-2 major 1·minor 3 + reviewer-1 minor)
- **(major) §0.5 PowerShell 프로브 파싱 오류 수정**: 이중따옴표 문자열 안 `"$c:"`를 PowerShell이
  스코프 변수로 파싱해 블록 전체가 ParserError로 죽던 버그(리뷰어 실행 재현) — `"${c}:"`
  중괄호 구분으로 수정, 수정 블록 실제 실행으로 오류 소멸 실측. 같은 블록·파일 전수 점검
  (bash 블록의 `"$c:"`는 bash 정상 문법, `$env:TEMP`는 유효 스코프 한정자 — 해당 없음).
- §0.5 선택지를 최대 4개로(AskUserQuestion options 스키마 상한 4 실측) — 웹 챗 복붙은
  선택지에서 빼 폴백 문장으로 전환. AskUserQuestion 툴이 없는 에이전트(Codex 등)는
  일반 텍스트 질문으로 대체함을 명시.
- §3.5 예외의 플러그인 폴더 탐지를 확장: 현재 폴더 직하만이 아니라 **상위 폴더 포함**
  `.claude-plugin/plugin.json` 발견 시 발동(하위 폴더에서 진행해도 적용).
- 워크스페이스 템플릿 CLAUDE.md의 "10. 도구(결정론)" 섹션이 표준 12섹션 목록 밖 추가라
  번호 매핑이 어긋나는 점을 템플릿 `_meta/deviations.md`에 기록(추가 자체는 허용).
- 맨몸 피험체 권장 1순위를 명시: ollama(구조적 무도구)·claude `--tools ""`(도구 빈값) —
  웹 미차단 피험체(codex·gemini)는 차선임을 표기.

## [0.2.0] - 2026-07-20
### Added
- **루트 에이전트 어댑터**: `CLAUDE.md`(= `@AGENTS.md` 포인터 1줄) + `AGENTS.md`(RUNBOOK 정본
  선언 + **변형 오프닝** — 첫 입력이 연구 질문이면 파일·웹 없이 맨몸으로 답하고, 그 답을
  튜토리얼의 맨몸 대조 재료로 쓰도록 안내). 타 에이전트(Codex 등)도 같은 정본으로 진행 가능.
- **RUNBOOK §0.5 사전 점검 업그레이드**(wiki-demo 규격): OS·python 실측 명령을 Windows
  PowerShell·Unix bash 양쪽으로 제시, 맨몸 대조용 LLM 도구(codex·claude·gemini·ollama)를
  `command -v`/`Get-Command`로 실측해 **관측된 도구만** 선택지 제시(웹 챗 복붙 폴백 포함),
  오염 가드(원문을 읽은 진행 세션의 즉석 맨몸 요약 금지) 명문화.
- **RUNBOOK §3.5 산출물 규약 신설**: 산출물은 사용자 워크스페이스 `artifacts/` 또는
  `40-drafts/`에만 — 플러그인 폴더(`${CLAUDE_PLUGIN_ROOT}`) 쓰기 금지, 이전 산출물은
  삭제 대신 `artifacts/prev-<날짜>/` 보존.
- **workspace-standards 명시 참조**: RUNBOOK 환경 전제·init SKILL.md에 표준 문서 경로 명기 —
  10단위 넘버링(`01-FOLDER_NUMBERING.md`)·CLAUDE.md 12섹션(`04-CLAUDE_MD_GUIDE.md`)·
  하네스 7-layer(`06-CLAUDE_CODE_AGENT_METHODOLOGY.md` §8.1)·강도 4단계(§8.2). init 템플릿 워크스페이스가
  표준 정합임을 재확인(CLAUDE.md 12섹션 실측).
### Changed
- RUNBOOK 진행 톤 규약 보강(wiki-demo 실측 교훈 반영): 톤 적용 범위 = 운영 브리핑 포함 모든
  산문 출력, 개인 말투 규칙보다 우선, 자기-계속 멘트 금지 사례 구체화, LaTeX 대체 표기(유니코드) 안내.
- `plugin.json` version 0.2.0. README 2종(영·한) 신규 기능 동기화.

## [0.1.0] - 2026-07-18
### Added
- 초기 릴리스. `/research-survey` 커맨드(라우터) + 3 스킬(main·init·run).
- 정본 대본 `RUNBOOK.md`(분 단위 튜토리얼) + references 6종(phase_contracts·taxonomy_dial·
  quality_gates·roles·citation_rules).
- **동봉 자립형 스크립트**(python3 stdlib): `skills/research-survey-run/scripts/classify.py`
  (범용 코퍼스 결정론 분류·랭킹·--sample) + `verify_summaries.py`(요약 결정론 검수).
- assets/templates: taxonomy 다이얼 · 서베이 섹션 · 자립형 대조표 HTML · workspace-standards
  준수 예시 워크스페이스(10단위 넘버링·CLAUDE.md **12섹션**·메타파일·`00-system/data-dictionary.md`).
- examples: ICML 2026 worked example(6,628편·9카테고리, 실제 편수·판정·사고 대응).
### Design
- 어댑터 층 아키텍처(정본 RUNBOOK + thin wrapper) — wiki-demo 참고.
- gptaku-plugins 규격 준수(plugin.json·`${CLAUDE_PLUGIN_ROOT}` 경로·README 이중언어).
- 범용 코퍼스 스키마(id/title/abstract/keywords?/url?/flags?)로 도메인 비결합 — 학회/arXiv 매핑만으로 동작.
- 콘텐츠 출처: DEV_TEAM ICML2026 서베이 실운영 기록(DEV_TEAM_PLAYBOOK.md).
- **`.claude-plugin/marketplace.json`** 추가 — 로컬 단일-플러그인 마켓플레이스(self-ref `source:"."`)로
  `claude plugin marketplace add <dir>` 원스텝 로컬 설치 지원.
### Verified
- cold-read 검수 루프(producer≠evaluator): worker 1차 FAIL(F1 스크립트 미패키징·F2 ICML 결합·
  F3 CLAUDE.md 12섹션 거짓·F4~F6) → master 수정 → worker 재검수 **PASS**(F1~F6 전건 해소,
  classify/verify 자립 실행 실측, end-to-end 새 사용자 자립 가능).
- **fresh 세션 설치 테스트 PASS**(격리 config dir): `claude plugin validate`✔ → `marketplace add`✔ →
  `install`✔(enabled) → `details`(4컴포넌트·~690tok) → `/research-survey help` 커맨드 라우팅·
  `${CLAUDE_PLUGIN_ROOT}` 해소 정상 → 자연어 자동발동으로 `research-survey-main` 스킬 발동·RUNBOOK 실행 확인.
