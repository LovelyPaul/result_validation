# Week 01 — 일단 돌아가게 만들기

> 스터디 정본 1주차("일단 돌아가게 만들기")를 research-survey 실기능에 매핑한 진행 가이드.
> 목표: 플러그인을 설치해 **한 바퀴 돌려보고**, 내 주제로 워크스페이스를 만들어 논문을
> 실제로 반입·분류하는 데까지. "감으로 검수"에서 벗어나는 출발점을 만든다.

## 이번 주 목표
- research-survey가 무엇을 하는 도구인지 **직접 돌려서** 이해한다(맨몸 요약 vs 근거 추적 서베이).
- 내 관심 주제로 워크스페이스를 만들고, 내 논문을 반입해 결정론 분류까지 돌린다.
- "무엇을·어떤 기준으로 검수할지"의 감을 잡는다(정식 EVAL 기준은 week02에서 손으로 만든다).

## 지금 할 일 (순서대로 · 각 단계 끝에서 확인)

### 1. 설치 + 데모 완주 (도구가 실제로 도는 걸 본다)
- 마켓플레이스/로컬로 플러그인을 설치한 뒤(README 빠른 시작), 동봉 샘플만으로 전 과정을 체험:
  ```
  /research-survey demo
  ```
- 데모는 6단계(+선택 채점)다: ①워크스페이스 스캐폴드 ②샘플 코퍼스·위키 노트 복사
  ③`classify`로 관련 7편 추출 ④위키 검색(1위 정답 확인) ⑤검수 거부 2종(출처 없음·Timeline
  변조) ⑥정상 승격 (⑦ 선택: 품질 채점). 정본 절차는 플러그인 `references/DEMO.md`.
- **여기서 배우는 것**: 근거가 추적되는 요약은 수치가 원문 페이지로 되짚어지고, 게이트가
  "그럴듯하지만 틀린" 산출물을 기계적으로 막는다.

### 2. 내 워크스페이스 만들기 (init)
```
/research-survey init <내-주제>
```
- workspace-standards 준수 워크스페이스가 생성된다(10단위 폴더·CLAUDE.md 12섹션·`AGENTS.md`
  자기소개 어댑터). 작업 지시 없이 워크스페이스를 열면 AGENTS.md가 진행 상황을 실측해
  다음 액션을 안내한다.
- **산출물**: `00-system/taxonomy.json`(관심 주제 다이얼 시드)·`PROJECT_STATUS.md`·12섹션 CLAUDE.md.

### 3. 내 논문 반입 (corpus_fetch) — 자기 주제로 전환
- RUNBOOK §2.5 "자기 주제로 바꾸기" 절차. arXiv id 목록 또는 검색어로 제목·초록을 원문
  그대로 범용 코퍼스로 가져온다(제목·초록은 arXiv export API verbatim — 손 편집 금지):
  ```
  # id 목록
  corpus_fetch.py --workspace . --ids 2512.17776,2303.08896
  # 검색어 + 최대 편수 (기존 코퍼스에 병합은 --append)
  corpus_fetch.py --workspace . --query "hallucination detection LLM" --max 10 --append
  ```
  (실제 실행은 플러그인 research-survey-run 스킬이 담당한다 — 위는 그 스킬이 내부에서 돌리는
  명령의 형태다. 반입 레코드에는 `source_grade: api_summary`·`retrieved_at`이 함께 기록된다.)

### 4. 다이얼 조정 + 결정론 분류 (classify)
- `00-system/taxonomy.json`의 카테고리를 내 주제로 맞춘 뒤 한 사이클 실행:
  ```
  /research-survey run <카테고리>
  ```
- 분류는 **결정론**이다(LLM 판단이 아니라 규칙) — 재현 가능하고 환각이 0이다. guard·relevance·
  noise·threshold가 무관 논문을 배제하는 것을 편수 diff로 본다.
- **산출물**: `70-analysis/`(categories·shortlist·summary)·분류 편수.

## 검수 개념 잡기 (week02 준비)
이 스터디의 할루시네이션은 세 유형이다 — **거짓/오출처**(없는 인용·틀린 수치)·**누락**(있어야
할 근거를 안 가져옴)·**부실**(대충 함). week01에서는 개념만 잡고, week02에서 gold 질문셋과
오류 매설 노트로 **직접 채점**한다.

## 완료 체크리스트
- [ ] `/research-survey demo`를 끝까지 완주했다(6단계 + 게이트 거부 2종을 눈으로 봤다).
- [ ] `/research-survey init <주제>`로 내 워크스페이스가 생겼다(AGENTS.md·taxonomy.json 확인).
- [ ] `corpus_fetch`로 내 주제 논문이 `60-data/corpus.json`에 실제로 들어왔다(파일 존재 확인).
- [ ] `/research-survey run`으로 분류가 돌아 `70-analysis/`에 편수·쇼트리스트가 생겼다.
- [ ] 손 검수 기준선 메모: "지금 이 결과물을 손으로 검수하면 얼마나 걸리고 무엇을 자주 놓치나" 한 줄.

## 이번 주 산출물
- 동작하는 내 워크스페이스 1개 · 내 주제 코퍼스(corpus.json) · 분류 결과(70-analysis/) ·
  손 검수 기준선 한 줄(4주 뒤 하네스와 비교용).

## 다음 주
week02 — 지식 창고(2분할 위키 노트)와 검수 기준(gold 질문셋·오류 매설·`wiki_grade` 채점)을
직접 만든다. `/research-survey curriculum week02`로 이어가세요. 다음으로 넘어갈까요?
