# verifier-kit — 도메인 중립 검수 코어 + 다이얼

`research-survey` 플러그인의 검증된 검수 로직(`verify_summaries.py`)에서 **"무엇을 검증할지"를
다이얼(JSON)로 외부화**한 킷이다. 코어는 도메인을 모르고, 다이얼이 안다. 새 검수 에이전트는
**코드가 아니라 다이얼 한 장**을 추가해 찍어낸다.

> 설계 근거: `taxonomy.json`이 "무엇을 모을지"를 코드 변경 0으로 바꾸듯, 이 킷은 "무엇을
> 검증할지"를 다이얼로 뺀다. 상세 방법론은 이 세션에서 만든 하네스 해부 아티팩트 참조.

## 무엇이 코어이고 무엇이 다이얼인가

| | 코어 (`verify_core.py` — 도메인 무관·수정 대상 아님) | 다이얼 (`dials/*.json` — 도메인이 정함) |
|---|---|---|
| 검사 로직 | 수치·인용이 원문에 substring 실재하는가(grep) | 어느 절에서 근거를 찾나 (`evidence_section`) |
| 오탐 회피 | 마스킹+스코프·숫자 경계·영어 수사 인정 | 무엇이 '좌표/메타'인가 (`coord_pattern`) |
| 규격 검사 | 섹션·인용·플레이스홀더·소스 표기 존재 검사 | 필수 섹션·인용 형태·소스 키가 무엇인가 |
| 원문 매핑 | fail-closed(해결 불가 시 FAIL) | 산출물→원문 id 형식 (`source_id_pattern`) |

**핵심: 발명 수치·오인용을 잡는 grep 로직 자체는 완전히 범용이다.** 도메인이 정하는 건
근거를 어디서·어떤 형태로 찾고, 원문을 어떻게 매핑하는가뿐이다.

## 검증 두 층 (원본과 동일 구조)

1. **규격(structural)** — 항상 실행. 플레이스홀더 0 · 필수 섹션 존재 · 근거 인용 ≥ `min_cites` · 소스 표기 존재.
2. **근거(grounding)** — `--corpus` 지정 시. 근거 절의 모든 수치(%·소수·정수)와 12자+ 인용
   문구가 원문에 실재하는지 대조. 부재 = **FAIL**. 원문 미해결 = **FAIL(fail-closed)** —
   조용한 생략은 매설 오류의 우회 루프홀이므로 막는다.

## 사용법

```bash
# 규격만 (원문 대조 없이)
python3 verify_core.py --dir <산출물 폴더> --dial dials/research-paper.json

# 근거 실재까지 (권장) — corpus.json 대비 수치·인용 grep
python3 verify_core.py --dir <폴더> --dial dials/research-paper.json \
  --corpus <corpus.json> [--source-dir <PDF추출 txt 폴더>]

# 자체 검사 (외부 의존 0)
python3 verify_core.py --self-test
```

반환: `0`=전건 PASS · `1`=FAIL 존재 · `2`=입력/다이얼 오류. → CI 게이트로 그대로 사용 가능.

## 다이얼 스키마

| 키 | 필수 | 의미 |
|---|---|---|
| `name` | ✓ | 다이얼 이름(리포트에 표기) |
| `required_sections` | ✓ | 반드시 존재해야 할 섹션 헤딩 배열 |
| `cite_pattern` | ✓ | 근거 인용으로 인정하는 정규식 (`min_cites`개 이상) |
| `source_marker` | ✓ | 원문 소스 표기 키(`<키>: <값>`의 값으로 원문 txt 매핑) |
| `evidence_section` | ✓ | 근거 실재 검사를 적용할 절 캡처 정규식 |
| `coord_pattern` | ✓ | 수치 추출 전 마스킹할 '좌표/메타'(주장 아님) 정규식 |
| `source_id_pattern` | ✓ | 산출물→원문 매핑 id 정규식(캡처그룹 1개) |
| `source_id_tagged` | | 태그형 id 우선 매칭(예: `arXiv:` 접두) |
| `source_id_full` | | 수치 needle 오추출 안전벨트(id의 full-match 형태) |
| `placeholder_pattern` | | 미작성 슬롯 신호 정규식 |
| `min_cites` | | 최소 근거 인용 수(기본 3) |
| `coverage_threshold` | | 키포인트 커버율 WARN 임계(기본 0.6) |

> JSON에서 정규식 백슬래시는 `\\`로 이스케이프한다. `_`로 시작하는 키(`_desc` 등)는 주석이며
> 코어가 무시한다.

## 검수기 채점 (G3) — "이 검수기를 믿을 수 있나?"

`grade_core.py`는 검수기 자체를 채점한다. 일부러 오염시킨 노트(**매설**)를 게이트에 통과시켜
**거부율**을 재고, 정상 노트(**대조군**)로 **과차단**까지 감시한다.

```bash
python3 grade_core.py --ev-dir ev/research-paper --dial dials/research-paper.json \
  --corpus ev/research-paper/corpus.sample.json --min-reject 0.8 [--report out.json]
python3 grade_core.py --self-test
```

- **이중 구현 금지**: 판정은 `verify_core`의 검사 함수를 그대로 호출한다 — 채점기와 검수기가
  다른 코드면 "채점은 통과, 실물은 실패"하는 괴리가 생긴다. 같은 코드 경로로 차단.
- **대조군 분리**: 거부율 분모는 매설만. 대조군을 섞으면 수치가 조용히 희석된다.
- 매설 노트는 검수 대상 md 상단에 메타 주석만 얹는다:
  `<!-- ev_type: invented-number -->` · `<!-- ev_expect: reject|pass|unchecked -->`
  (기본 reject. `pass`=대조군, `unchecked`=fail-closed 시연).

동봉 스위트(`ev/research-paper/`) 5매설 + 1대조군 실측: **거부율 100% · 과차단 0 · fail-closed 1**.

| 매설 노트 | 유형 | 잡는 층 |
|---|---|---|
| ev-invented-number | 원문에 없는 수치 92.4 | grounding |
| ev-quote-miscite | 원문에 없는 따옴표 인용 | grounding |
| ev-missing-section | 필수 섹션 누락 | structural |
| ev-no-source | 소스 표기·인용 부족 | structural |
| ev-unresolved-source | 코퍼스 미등재 id → unchecked | grounding(fail-closed) |
| ev-clean-control | 정상(모든 수치 실재) → 통과 | — (과차단 감시) |

## 두 번째 에이전트 = 코드 리뷰 (아키텍처 검증)

`dials/code-review.json` + `ev/code-review/`는 **`verify_core.py`를 한 줄도 안 고치고** 만든
두 번째 도메인 에이전트다. 논문↔코드 리뷰 매핑:

| | 논문 | 코드 리뷰 |
|---|---|---|
| 근거 절 | `## Evidence` | `## 변경 근거` |
| 인용 형태 | `p.6`·`Table 1` | `src/auth.py:42`·`test_x` |
| 원문(소스) | arXiv 초록·PDF txt | diff·테스트 출력 |
| 매핑 id | arXiv id | `PR#123` |
| 발명 차단 | 원문에 없는 수치·인용 | diff에 없는 커버리지·테스트 결과 문구 |

**다이얼 설계 교훈(실측에서 나옴)**: 처음엔 `cite_pattern`에 `PR#\d+`를 넣었더니, 파일:라인
근거를 하나도 안 댄 리뷰가 하단 `source_diff: PR#123` 표기만으로 인용 2개를 충족해 새어나갔다.
**PR번호·커밋해시는 '무엇을 봤나'(근거)가 아니라 '어느 변경인가'(좌표)** 라 인용에서 빼야 한다
(논문 다이얼이 arXiv id를 인용으로 안 세는 것과 동일). 이 결함은 **코어가 아니라 다이얼에서**
고쳐졌다 — 설계가 올바르다는 신호다.

## CI 게이트 (G6) — 검수기가 약해지면 빌드를 막는다

`ci/run-gate.sh`는 로컬·CI 동일 진입점이다(이중 구현 금지 — CI가 로컬과 다른 명령을 쓰면
"로컬은 통과, CI는 실패" 괴리가 생긴다). 하는 일:

1. `verify_core`·`grade_core` self-test (엔진 무결성)
2. **다이얼 자동 발견** — `dials/*.json` 각각에 대해 `ev/<다이얼명>/` 매설 스위트를 채점.
   거부율 < `MIN_REJECT`(기본 0.8)이거나 대조군 과차단이면 exit 1.

```bash
bash verifier-kit/ci/run-gate.sh          # 전체 게이트
MIN_REJECT=1.0 bash verifier-kit/ci/run-gate.sh
```

**새 에이전트를 추가해도 CI를 안 고친다** — `dials/X.json` + `ev/X/`(코퍼스 포함)만 두면
러너가 자동으로 채점 대상에 넣는다. ev 스위트 없는 다이얼은 경고(스킵), 코퍼스 없으면
fail-closed(exit 1).

GitHub Actions(`.github/workflows/verifier-gate.yml`)가 `verifier-kit/**` 변경 push·PR마다
이 러너를 돌린다. 표준 라이브러리만 쓰므로 의존성 설치 단계가 없다.

> 게이트가 진짜로 막는지 실측: 매설 노트를 정상으로 오염시켜 거부율 100%→75%로 떨구면
> `MIN_REJECT=0.8` 게이트가 exit 1로 잡는다(검수기가 약해지면 CI가 자동 차단).

## 새 검수 에이전트 찍어내기 (다이얼 추가만)

1. `dials/<도메인>.json`을 만든다 — 위 스키마대로 그 도메인의 근거 규칙을 채운다.
   - **코드 리뷰** (구현됨 — `dials/code-review.json` + `ev/code-review/`): `evidence_section` =
     `## 변경 근거`, `cite_pattern` = 파일:라인·테스트명(PR#·해시는 '좌표'라 근거로 안 셈),
     `source_id_pattern` = `PR#(\\d+)`, 원문 = diff·테스트 출력. 거부율 100%·과차단 0 실측.
   - 예) **문서 팩트체크**: `evidence_section` = `## 근거`, `cite_pattern` = 조항/페이지,
     `source_id_pattern` = 문서 id, 원문 = 원본 조항 txt.
2. `--dial dials/<도메인>.json`으로 실행한다. **코어는 손대지 않는다.**
3. 그 도메인의 **매설 스위트**(`ev/<도메인>/` + `corpus.sample.json`)를 만든다 —
   `ev/research-paper/`·`ev/code-review/`를 템플릿으로. `ci/run-gate.sh`가 자동 발견해
   채점하므로 CI 설정은 건드릴 필요 없다.

## 이관 출처·검증

- 코어 로직은 `../skills/research-survey-run/scripts/verify_summaries.py`에서 이관(재작성 아님).
- `verify_core.py --self-test` → **SELF-TEST PASS** (원본 fixture 이식·경계 조건 회귀 포함).
- 외부 다이얼 파일(`dials/research-paper.json`)로 발명 수치(`94.2%`) 탐지·정상 노트 통과 실측 확인.

## 로드맵 (6대 보완점 대응)

- [x] **G1** 골격 복제 — 2층 검증 코어 이관
- [x] **G2** 스키마 외부화 — 도메인 상수를 다이얼로
- [x] **G3** 매설 스위트 — `grade_core.py` + `ev/research-paper/`(거부율 100%·과차단 0 실측)
- [x] **두 번째 다이얼** — `dials/code-review.json` + `ev/code-review/`. **코어 무수정**으로
      코드 리뷰 검수 에이전트 동작(거부율 100%). 아키텍처 검증 완료 — 도메인 결함은 다이얼에서 해결.
- [x] **G6** CI 배선 — `ci/run-gate.sh`(다이얼 자동 발견) + GitHub Actions. 거부율 하락 시
      PR 차단(실측: 100%→75% 오염 시 exit 1). 새 에이전트 추가해도 CI 무수정.
- [ ] **G1+** 의미 채널 — 임베딩/NLI를 WARN급 보조로 (판정 권한은 결정론 유지)
- [ ] **거부율 추세 추적** — CI 리포트를 아티팩트로 적재해 거부율 시계열 감시
