# Changelog

All notable changes to this plugin are documented here (Keep a Changelog style).

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
    `id/title/source` + 출처 인용 존재)를 코드로 강제해 "정본 직접 쓰기 금지" 계약을 집행,
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
