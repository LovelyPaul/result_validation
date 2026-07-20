[English](README.md) | 한국어

# research-survey

> 관심 연구 주제를 **근거가 추적되는 서베이**로 — 추출 → 요약 → 3중 검증 → 인사이트·가설 →
> 새 논문 지속 추적까지. "맨몸 LLM 요약"과 "근거 서베이"의 차이를 배우고 직접 돌린다.

- [빠른 시작](#빠른-시작)
- [왜 research-survey인가](#왜-research-survey인가)
- [동작 원리](#동작-원리)
- [구성](#구성)
- [요구사항](#요구사항)
- [라이선스](#라이선스)

## 빠른 시작
```
/plugin marketplace add <owner>/gptaku-plugins   # 또는 로컬 경로
/plugin install research-survey
# Claude Code 재시작 후:
/research-survey demo              # 동봉 샘플로 5~10분 toy 체험 (추출 → 위키 검색 → 게이트 거부 → 승격)
/research-survey tutorial          # 파이프라인 라이브 학습 (~15분)
/research-survey init <주제>       # 표준 준수 워크스페이스 생성
/research-survey run <카테고리>    # 한 카테고리 1사이클 실행
```

**내 논문 가져오기**: `corpus_fetch.py --ids <arXiv id들>` 또는 `--query "<검색어>" --max N`이
arXiv export API에서 제목·초록을 원문 그대로 범용 코퍼스 스키마로 반입한다(`--append`는 병합·
중복 id 스킵) — 그다음 taxonomy 다이얼을 내 주제로 고치고 classify를 재실행하면 된다.
지속 서베이는 `--since YYYY-MM-DD`를 붙이면 마지막 반입 이후 제출분만 가져온다(델타 모드·
`--append`와 병용).

**사용 모드 2종:**
1. **마켓플레이스 설치**(위 방법) — 플러그인은 command/skill로 동작하며, 리포 루트의
   `CLAUDE.md`/`AGENTS.md` 어댑터는 여러분 프로젝트에 **로드되지 않는다**.
   `/research-survey`(또는 자연어 트리거)로 시작한다.
2. **clone 후 리포로 `cd`** — 루트 어댑터가 유효: `AGENTS.md`를 읽는 어떤 에이전트(Codex 등)든
   같은 RUNBOOK으로 진행하고, **변형 오프닝**이 동작한다(첫 입력으로 연구 질문을 던지면
   그 맨몸 답이 대조 재료가 된다).

## 왜 research-survey인가
"맨몸 LLM 요약"은 그럴듯하지만 출처가 없다. **근거 서베이**는 모든 수치를 논문 페이지로
되짚는다(`— Table 1, p.6`). 그리고 **producer≠evaluator 3중 검증**으로 환각을 거른다.
이 플러그인은 그 차이를 가르치고 실제로 돌린다.

## 동작 원리
```
[다이얼]  taxonomy.json 이 관심 주제를 정의 (이 파일 하나가 스냅샷 추출 + 매일 신착 매칭을 동시 지배)
   → [추출]   결정론 다중라벨 분류 (재현 가능·환각0)
   → [선별]   쇼트리스트
   → [요약]   논문별 PDF 실측 요약 (4절 + 페이지 인용 Evidence + source_pdf)
   → [검증]   ★3중: 자가검증 → 독립 실측 → 표본 PDF 대조
   → [정리]   wiki 색인·검색(FTS5 + 문자 bigram BM25) + 승격 게이트 → Notion(선택) + 인사이트 추출
   → [가설]   idea-critic 채점(reviewer + inspector) → accept/hold → ledger
   → [지속]   매일 arXiv 신착을 같은 다이얼로 매칭 → 다이제스트
```

## 구성
| 컴포넌트 | 역할 |
|---|---|
| `/research-survey` 커맨드 | 라우터: `tutorial` / `demo` / `init` / `run` / `help` |
| `demo` 체험(`references/DEMO.md`) | 설치 직후 동봉 샘플 toy 완주: 스캐폴드 → 코퍼스+위키 노트 3개 복사 → classify(15편 중 7편 추출) → 근거 발췌 위키 검색 → 게이트 거부 시연 2종(출처 없음·Timeline 변조) → 정상 승격 |
| `corpus_fetch.py` | 내 논문 반입 — arXiv export API에서 `--ids`/`--query --max`로 제목·초록 원문 verbatim 수집, `--append` 중복 스킵 병합(범용 코퍼스 스키마). `--since YYYY-MM-DD` 제출일 필터로 지속 서베이 델타 반입(published 결측은 fail-closed 제외)·연결층 오류(오프라인/DNS/타임아웃) 명시 진단 |
| `research-survey-main` 스킬 | 라이브 튜토리얼 + 오케스트레이션 (정본은 RUNBOOK) |
| `research-survey-init` 스킬 | workspace-standards 워크스페이스 스캐폴딩(10단위 넘버링·CLAUDE.md 12섹션·하네스 7-layer — 표준 문서를 경로로 명시 참조) |
| `research-survey-run` 스킬 | 한 카테고리 사이클: 추출 → 요약 → 3중검증 → 정리 |
| wiki 검색·승격 레이어 | 계약이 아니라 **실제 동작 도구**: `wiki_index.py`(SQLite FTS5 색인 또는 순수 파이썬 문자 bigram BM25 폴백), `wiki_query.py`(FTS5 매치 + bigram BM25를 RRF K=60로 융합·채널 내 중복 id 방어, dangling 0 위키링크), `wiki_promote.py`(dry-run diff → `--apply` 게이트·frontmatter+출처 lint·JSONL manifest). BM25 수식은 tax-wiki 데모에서 그대로 이식(ablation 검증) |
| 품질 채점 하네스 | `wiki_grade.py` — gold 질문셋(질문·기대 1위 노트·기대 근거 문구, 동봉 샘플 12문항)으로 **1위 적중률·top-k recall**, 오류 매설 노트(동봉 5유형: 발명 수치·문구 오인용·출처 없음·Timeline 변조·필수키 누락 + 통과가 정상인 clean 대조군 1개 — 과차단 감시)로 **게이트 거부율**을 채점. gold 근거 문구의 비어있지 않음·노트 실재도 검사(fail-closed). JSON 리포트 + `--min-top1`/`--min-reject` 임계 게이트. 동봉 샘플 실측: 적중 12/12·매설 거부 5/5·대조군 통과 |
| source-coverage 검수 | `verify_summaries.py --corpus` — Evidence의 수치(퍼센트·소수·**정수 전부** — 인용 좌표·목차 번호 마스킹, 연도형 4자리 제외, 숫자 경계 매칭, 소형 정수는 영어 수사 표기 인정)·인용 문구가 원문(`--source-dir` PDF 추출 txt 우선, 없으면 코퍼스 초록)에 실재하는지 grep 대조(원문 미해결=FAIL·fail-closed), 초록 키포인트 커버율이 임계(기본 0.6) 미달이면 WARN |
| 유지보수 루프 | `wiki_index.py --audit` — **stale** 30일 감지(`updated`/`created` 나이·날짜 파싱 불가는 fail-closed), 건강도 1줄(notes/edges/orphan/broken/stale/skipped), **타입드 엣지** `[[id\|rel]]`(contrasts/supports/extends)와 contrasts 쌍 목록, 노트 `confidence` 선언(직접 인용 1.0/요약 0.7) manifest 기록 |
| 루트 `CLAUDE.md` + `AGENTS.md` | 에이전트 어댑터 — 어떤 에이전트(Codex 등)든 같은 RUNBOOK으로 진행. **변형 오프닝**: 첫 입력이 연구 질문이면 파일·웹 없이 맨몸으로 답하고, 그 답이 "맨몸 vs 근거 서베이" 대조 재료가 된다 |
| RUNBOOK §0.5 사전 점검 | OS·python·LLM CLI를 실측(`command -v`/`Get-Command`, Windows·Unix 명령 양쪽 제시) — **실측된 도구만** 맨몸 피험체 선택지로 제시, CLI가 없으면 웹 챗 복붙 폴백 |
| RUNBOOK §3.5 산출물 규약 | 산출물은 사용자 워크스페이스 `artifacts/` 또는 `40-drafts/`에만 — 플러그인 폴더 쓰기 금지, 이전 산출물은 삭제 대신 `artifacts/prev-<날짜>/` 보존 |
| references/ | RUNBOOK · phase_contracts · taxonomy_dial · quality_gates · roles · citation_rules |
| assets/templates/ | 다이얼 · 서베이 섹션 · 자립형 대조표 HTML · 예시 워크스페이스 |
| examples/ | ICML 2026 worked example(6,628편·9카테고리 — 실제 편수·판정·사고 대응) |

## 요구사항
- Claude Code. 코어 튜토리얼은 로컬만으로 진행(분류·검수 스크립트는 python3 표준 라이브러리).
- 선택: 논문 코퍼스(제목·초록·PDF)와 목적지(Notion·wiki).

## 라이선스
MIT

<p align="center"><sub>서베이는 재사용 가능한, 출처가 달린 구조를 남길 때만 쓸모가 있다.</sub></p>
