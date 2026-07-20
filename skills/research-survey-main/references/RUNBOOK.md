---
title: research-survey RUNBOOK (정본 대본)
version: 0.4.0
duration: 15-20분 (코어) + 확장
role: 진행자(에이전트)가 이 대본을 읽고 라이브로 튜토리얼을 진행한다
---

# RUNBOOK — 관심 주제 연구 서베이, 라이브 튜토리얼 정본 대본

> 이 파일이 SOT다. command·skill·AGENTS.md는 전부 이 대본을 가리키는 thin wrapper.
> 에이전트 없이 사람이 이 대본만 읽고 수동으로 따라 해도 동작하도록 쓴다.

## 진행 톤 규약 (불변)
- 존댓말·비전문가 눈높이. 전문용어는 **처음 나올 때 글로서리 문장으로** 풀고, 이후 그 문장으로 통일.
- **적용 범위 = 튜토리얼 진행 중의 모든 산문 출력.** 청중용 대사만이 아니라 운영 브리핑
  ("환경 확인했습니다", "이제 검증 단계로 갈까요?")까지 전부. 예외는 명령어·코드·도구 실행
  출력뿐. (wiki-demo 1회차 실측 교훈: 대사만 존댓말이고 브리핑은 반말 로그체로 갈라져 톤이 깨졌다.)
- **이 톤 규칙은 에이전트가 다른 곳에서 로드한 개인 말투 규칙(반말·압축체 등)보다 우선한다**
  — 튜토리얼 모드에 들어간 순간부터.
- **각 단계는 반드시 질문으로 끝낸다.** "다음으로 넘어갈까요?" — 자기-계속(자동 진행) 암시 멘트 금지.
  "잠시만 기다려 주세요"처럼 자기가 이어갈 것처럼 말해놓고 멈추는 멘트도 금지 (wiki-demo 실측:
  진행자가 왜 안 넘어가냐고 되물어야 했다). 사용자가 "쭉 진행해"라고 명시하면 그때부터 연속 진행.
- 수치·인용은 **원문 근거와 함께**. 근거 없으면 "확인 안 됨"이라 말하고 지어내지 않는다(precision 우선).
- 출력에 LaTeX 금지(터미널·슬라이드 렌더 깨짐 — `$\times$`가 원문 그대로 보인다). 기호가 필요하면
  유니코드 문자(×, →, ≥)를 직접 쓰거나 한글로 푼다. 표·코드블록·blockquote만 사용.

## 용어 글로서리 (나올 때마다 이 문장으로)
| 용어 | 풀이 |
|---|---|
| taxonomy 다이얼 | 관심 주제를 정의하는 규칙 파일. 이거 하나만 바꾸면 무엇을 모을지가 바뀐다. |
| 카테고리(category) | 다이얼 안의 한 관심 주제(예: "LLM 사전학습", "의료 데이터 생성"). |
| 쇼트리스트(shortlist) | 카테고리에서 상위로 뽑힌, 정독·요약할 논문 목록. |
| 근거 인용(evidence) | 요약의 각 수치·주장 옆에 붙는 "— Table X, p.Y" 원문 위치. |
| producer≠evaluator | 만든 사람이 자기 것을 채점하지 않는다. 검수는 다른 좌석이 원문만 보고 한다. |
| cold-read | 저자 의도·배경 없이 산출물과 원문만으로 검증하는 것. |
| 3중 검증 | 자가검증 → 독립 실측 → 표본 원문 대조. 셋 다 통과라야 완료. |
| 가설(hypothesis) | "If we change X under fixed Y, metric Z will… because…" 형식의 검증가능 명제. |
| 지속 서베이 | 새 논문(arXiv 등)을 같은 다이얼로 매일 자동 매칭해 이어가는 것. |

## 환경 전제
- 논문 코퍼스(제목·초록·PDF)와 taxonomy 다이얼(JSON)이 있으면 어디서든 동작.
- **코퍼스가 없으면 동봉 샘플로 실데이터 진행** — `../assets/templates/workspace/`의
  `60-data/corpus.sample.json`(15편: 스터디 주제 '리서치 검수 하네스' 관련 7편 — DEER·CRITIC·
  SelfCheckGPT·LLM-as-a-Judge·ChatEval·G-Eval·할루시네이션 서베이, 전건 arXiv 실측 검증 — +
  무관 8편: VLM 토큰압축·병리 MLLM 등, 실코퍼스 verbatim)과 `00-system/taxonomy.sample.json`
  (해당 주제 1카테고리 다이얼)을 워크스페이스의 `60-data/corpus.json`·`00-system/taxonomy.json`
  으로 복사하면 [추출]부터 전 단계가 라이브로 돈다(실측: 관련 7/7 분류·무관 오탐 0).
  worked example(`../examples/icml2026-worked-example.md`, ICML 2026 6,628편)은 낭독 모드 보조 재료.
- 의존성: python3(표준 라이브러리)만. 분류·검수 스크립트는 **플러그인에 동봉**:
  `${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/{classify.py, verify_summaries.py}`.
  외부 API 없이 로컬만으로 코어 진행 가능. 코퍼스 스키마는 워크스페이스 `00-system/data-dictionary.md`.
- **표준 베이스캠프 = workspace-standards.** 워크스페이스 구조·문서 규약은 이 표준을 따른다.
  아래 요지만으로 진행 가능하며, 상세 원문은 각 경로(표준 리포 문서)에 있다:
  - **10단위 폴더 넘버링** (`workspace-standards/01-FOLDER_NUMBERING.md`) — 폴더는 2자리 숫자
    접두(`00-system/`, `10-planning/`, …, `90-archive/`)로 시작한다. 탐색기 정렬이 항상 같고,
    중간 삽입 여유(05, 15…)가 있다. 넘버링/비넘버링 혼용 금지.
  - **CLAUDE.md 12섹션 스키마** (`workspace-standards/04-CLAUDE_MD_GUIDE.md`) — ①제목+한 줄 설명
    ②대상 런타임 ③정체성(허용/금지) ④핵심 원칙 ⑤폴더 구조 ⑥워크플로우 ⑦커맨드 목록
    ⑧Scale Modes(Lite/Standard/Full) ⑨트리거 경계 ⑩도메인 프레임워크 ⑪산출물 형식
    ⑫품질 규칙+변경 이력. "One Workspace, One Agent" — 워크스페이스 하나가 특화 에이전트 하나.
  - **하네스 7-layer** (`workspace-standards/06-CLAUDE_CODE_AGENT_METHODOLOGY.md` §8.1) —
    워크스페이스는 폴더 모음이 아니라 AI 작업의 통제 환경(하네스)이다: instruction surface
    (CLAUDE.md)·commands·agents·skills·hooks·state·memory 7층이 합쳐져 하나의 특화 에이전트가
    된다. 하네스 강도 4단계(basic/runtime-ready/runtime-enforced/meta-harness)는 같은 문서 §8.2.
  - init 스킬이 만드는 워크스페이스 템플릿(`../assets/templates/workspace/`)은 이 표준을 준수한다.

---

## §0 — 인트로 스크립트 (약 1분)

> "안녕하세요. 오늘은 **관심 있는 연구 주제로 논문을 서베이하는 전 과정**을 함께 보겠습니다.
> 오늘 배울 한 줄: **'맨몸 LLM에게 요약시키는 것'과 '근거가 추적되는 서베이'는 전혀 다른 결과를
> 냅니다.** 전자는 그럴듯하지만 출처가 없고, 후자는 모든 수치가 원문 페이지로 되짚어집니다.
> 순서는 이렇습니다: ①주제를 다이얼로 정의 → ②논문 추출 → ③원문 실측 요약 → ④3중 검증으로
> 환각 제거 → ⑤인사이트·가설·서베이로 정리 → ⑥매일 새 논문 자동 추적. 첫 사례로 논문 한 편을
> '맨몸 요약'과 '근거 서베이'로 나란히 비교해볼까요?"

## §0.5 — 사전 점검 (인트로 직후, 코어 전 필수 · 약 1-2분)

받는 사람 환경에 특정 CLI가 있으란 보장이 없다. 추측하지 말고 실측한다.

**① OS·python 실측** — 명령으로 확인한다 (양쪽 제시 — 환경에 맞는 쪽 실행).

```bash
# macOS/Linux (셸이 bash/zsh일 때)
uname -s 2>/dev/null || echo Windows
python3 --version 2>/dev/null || python --version
for c in codex claude gemini ollama; do command -v $c >/dev/null 2>&1 && echo "$c: 있음"; done
command -v ollama >/dev/null 2>&1 && ollama list   # 로컬 모델 목록까지 실측
```

```powershell
# Windows (PowerShell)
"OS: Windows $([System.Environment]::OSVersion.Version)"
if (Get-Command python -ErrorAction SilentlyContinue) { python --version } elseif (Get-Command py -ErrorAction SilentlyContinue) { py -3 --version } else { "python: 없음" }
foreach ($c in "codex","claude","gemini","ollama") { if (Get-Command $c -ErrorAction SilentlyContinue) { "${c}: 있음" } }
if (Get-Command ollama -ErrorAction SilentlyContinue) { ollama list }
```

Windows면 이후 모든 명령의 경로 구분자·`cp`·`mkdir -p`를 PowerShell식으로 바꿔 실행한다
(`cp` → `Copy-Item`, `~` → `$HOME`, **`python3` → `python` 또는 `py -3`** — 이 문서·DEMO.md의
모든 코드 블록에 적용).

**② 맨몸 대조용 LLM 도구 선택 질문** — [요약·맨몸 대조] 단계에서 "맨몸 LLM 요약"을 만들
피험체를 고른다. **①에서 실측된 도구만 선택지에 올린다 — 실측 안 된 도구는 선택지 금지.**
AskUserQuestion 툴 JSON으로 묻는다(**선택지는 최대 4개** — 툴 스키마의 options 상한이 4다).
웹 챗 복붙은 선택지에 넣지 말고 질문 끝에 폴백 문장으로 안내한다. AskUserQuestion 툴이 없는
에이전트(Codex 등 — 루트 `AGENTS.md`로 진행하는 경우)는 같은 내용을 일반 텍스트 질문으로 묻는다.
예시:

> 이 환경에서 확인된 AI 도구는 다음과 같아요. 어느 것으로 "근거 없이 맨몸으로 요약하기"를 해볼까요?
> 1. codex
> 2. claude (Claude Code — 새 프로세스)
> 3. gemini (Gemini CLI)
> 4. ollama (로컬 모델: 방금 확인된 목록)
>
> (CLI를 쓰기 어려우시면 웹 챗 복붙으로도 됩니다 — 제가 요약 지시문을 드리면 쓰시는
> 채팅창(ChatGPT, Gemini 등)에 붙여넣고 답을 가져와 주세요.)

**맨몸 요약 지시문 (원문 — 이대로 사용, 즉석 변형 금지)**:

```text
웹 검색·파일·도구 접근 없이, 이미 알고 있는 학습지식만으로 답하세요.
모르는 내용은 모른다고 답하세요 — 추측으로 메꾸지 마세요.
다음 논문을 요약해 주세요: <제목·저자·연도(·있으면 arXiv ID)>
포함할 것: ①무엇을 했나 ②핵심 기법 ③주요 수치 결과 ④한계
```

**피험체 실행 위치**: 반드시 **플러그인 폴더 밖의 빈 폴더**에서 실행한다
(bash: `L0DIR=$(mktemp -d); cd "$L0DIR"` / PowerShell:
`$L0DIR = New-Item -ItemType Directory "$env:TEMP\bare-$(Get-Random)"; cd $L0DIR`) —
파일 도구가 있는 에이전트는 작업 폴더를 자동 탐색해 원문·references를 읽어버릴 수 있다.

**권장 피험체 1순위 = ollama(구조적으로 도구·웹 접근이 없음) 또는 claude `--tools ""`(도구
빈값 지정)** — 웹 검색이 차단되지 않는 codex·gemini는 차선이다(지시문 문구 준수에 의존).

도구별 실행 형태(있는 것만·모델 지정은 선택):

```bash
claude -p --tools "" [--model <별칭>] '<위 지시문>'   # --tools "" = 모든 내장 도구 비활성 (claude --help 실측 확인)
codex exec --skip-git-repo-check [--model <이름>] '<위 지시문>'
gemini -p '<위 지시문>'
ollama run <ollama list의 모델 이름> '<위 지시문>'
# 웹 챗 경로: 위 지시문을 사용자에게 주고 붙여넣게 한 뒤 답을 받아온다
```

- 도구차단 플래그는 **실존이 확인된 것만** 쓴다. 확인된 것: claude `--tools ""`(모든 내장 도구
  비활성 — help 원문 "Use \"\" to disable all tools"). codex·gemini·ollama는 "전체 도구 차단"
  플래그가 확인되지 않았다 — codex `-s read-only`는 셸 명령 쓰기 제한(읽기·검색 차단 아님),
  gemini `--approval-mode plan`은 read-only 모드(읽기 도구는 동작)일 뿐이다. 이들은
  **지시문 문구 + 빈 폴더 cwd**로 통제하고, 진행 중 피험체가 도구를 쓴 정황이 보이면 그
  사실을 청중에게 알린다.

- 어떤 도구도 없으면 웹 챗 복붙 경로로 진행한다 — 튜토리얼 성립에 CLI가 필수는 아니다.
- 세션의 첫 입력이 연구 질문이었다면(루트 `AGENTS.md`의 변형 오프닝) 그때 받아둔 맨몸 답을
  대조 재료로 그대로 써도 된다 — 별도 피험체 실행 생략 가능.
- **금지**: 이미 RUNBOOK·원문 PDF를 읽은 진행 세션이 새 프로세스도 안 띄우고 그 자리에서
  "맨몸 요약"을 답하는 것 — 컨텍스트에 근거가 있어 대조가 조용히 무효가 된다. 사용자가 이걸
  요청하면 솔직하게 알리고 새 프로세스 또는 웹 챗 경로를 안내한다.

**③ 진행 모드 선택** — **AskUserQuestion 툴 JSON으로** 묻는다:
   - show(시연): 한 논문/카테고리 통쏘기 대조 [기본]
   - build(구축): 표준 워크스페이스 만들고 한 사이클 실제 실행
   - explore(탐색): 즉석 질문을 다이얼로 매칭

---

## §1 — 코어 (분 단위 진행표)

| 분 | 단계 | 화면에서 일어나는 일 |
|---|---|---|
| 0–2 | **[다이얼]** 관심 주제 정의 | taxonomy.json에서 카테고리 하나를 보여주고, patterns/relevance/noise/threshold가 "무엇을 모을지"를 어떻게 정하는지 설명 |
| 2–4 | **[추출]** 결정론 분류 | 분류기를 돌려 코퍼스 → 카테고리별 편수·oral 우선 랭킹. "왜 LLM 판단이 아니라 규칙인가"(재현·환각0) |
| 4–5 | **[선별]** 쇼트리스트 | 상위 N편을 뽑아 초록 미리보기 |
| 5–7 | **[요약·맨몸 대조]** | 같은 논문을 (a)맨몸 LLM 요약 (b)PDF 실측 요약(Summary 4절+Evidence 페이지인용)으로 나란히 |
| 7–10 | **[검증]** 3중 검증 시연 | 자가검증(grep) → 독립 실측 → 표본 원문 대조. 발명 수치·페이지 오인용이 어떻게 걸리는지 |
| 10–12 | **[인사이트]** | 쇼트리스트에서 주제 클러스터·트렌드·연구 갭 추출 |
| 12–14 | **[가설]** | 갭에서 falsifiable 가설 1개 작성 → idea-critic 채점(novelty·feasibility·impact) → accept/hold |
| 14–15 | **[정리·지속]** | 대조표 HTML 1장 생성 + 검증 통과 요약을 wiki 정본으로 승격(`wiki_promote` dry-run→apply)하고 `wiki_query`로 되찾아 보이기 + "매일 arXiv 자동 추적"으로 이어지는 구조 설명 |

### 각 단계 배너 (출력 형식)
각 단계 시작 시 한 줄 배너로 위치를 알린다:
`▶ [3/8] 요약 — 같은 논문, 맨몸 vs 근거 추적을 비교합니다`

### 단계별 핵심 포인트 (청중이 주목할 것)
- **[다이얼]**: 다이얼 파일 한 줄(noise_terms)만 바꿔도 결과 편수가 달라지는 것 — "조정은 편집 하나".
- **[추출]**: guard 정규식이 무관 논문을 어떻게 배제하는가(예: "medical" 가드가 비의료 배제).
- **[요약 대조]**: 맨몸 요약은 "SOTA를 달성했다"류로 뭉개지고, 근거 요약은 "Entity F1 39.11 vs
  SFT 18.73 — Table 1, p.6"처럼 되짚어진다. **이 대비가 오늘의 핵심.**
- **[검증]**: 요약 착수 전 "PDF 1페이지 제목 ↔ 목록 제목" 대조(엉뚱한 논문 요약 방지) 시연.
- **[가설]**: hold가 실패가 아니라 "게이트가 작동한 것"임을 강조 — 근거 없는 아이디어가 승격되지 않음.
- **[정리·지속]**: wiki 레이어가 계약이 아니라 **실제 동작하는 도구**임을 보인다 — 검증 통과 요약을
  `wiki_promote`로 정본 승격(dry-run diff → 승인 → apply, 출처 없는 노트는 게이트가 거부),
  `wiki_index`로 색인, `wiki_query`로 같은 질문을 다시 던져 근거 발췌를 되찾아 보여준다.
  "한 번 요약하고 끝이 아니라, 검색·되찾기 가능한 정본으로 쌓인다"가 핵심.

---

## §2 — 캡처 전환 규약 (라이브가 어긋날 때)
- 실시간 분류·검색이 예상과 다르면, examples의 사전 캡처(편수·판정 수치)로 전환해 서사를 유지한다.
- "지금은 미리 돌려둔 결과로 보겠습니다"라 정직히 알리고 진행. 라이브 실패를 숨기지 않는다.

## §2.5 — 자기 주제로 바꾸기 (샘플 → 내 서베이)

데모·튜토리얼의 전 과정은 파일 2개만 바꾸면 내 주제로 그대로 돈다:
1. **다이얼 수정**: 워크스페이스 `00-system/taxonomy.json`의 카테고리를 관심 주제로 교체
   (patterns/relevance_terms/noise_terms/threshold — 작성법은 `taxonomy_dial.md`).
2. **논문 반입**: `corpus_fetch.py`로 원하는 논문을 범용 스키마로 가져온다(제목·초록은
   arXiv export API 원문 verbatim — 손 편집 금지):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/corpus_fetch.py" --workspace . --ids 2512.17776,2303.08896
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/research-survey-run/scripts/corpus_fetch.py" --workspace . --query "hallucination detection LLM" --max 10 --append
   ```
   `--append`는 기존 코퍼스에 병합(중복 id 자동 스킵).
3. **재추출**: `classify.py --workspace .` 재실행 → 편수 diff를 보고 다이얼을 조정한다
   (§3 다이얼 조정 루프). 이후 요약→검증→승격은 §1 코어와 동일.

## §3 — 확장 모듈 (시간 남으면)
- **toy 데모(`/research-survey demo`)**: 설치 직후 5~10분 자동 체험 — 정본 `DEMO.md`
  (샘플 코퍼스 추출→위키 검색→검수 거부 2종→정상 승격).
- **다이얼 조정 루프**: noise_terms/relevance_terms를 즉석에서 바꿔 재추출 → before/after 편수 diff.
- **새 카테고리 추가**: taxonomy에 관심 주제 1개 추가 → 추출까지. "새 주제는 코드 변경 0".
- **wiki 검색·승격 실연**: 검증 통과 요약을 `wiki_promote`로 정본 승격(dry-run→apply·출처 게이트),
  `wiki_index`로 색인(FTS5 가용 시 FTS5+bm25(), 불가 시 순수 파이썬 bigram BM25 폴백 + 링크
  엣지 추출·orphan/broken 감사), `wiki_query`로 한국어·영어 질문을 던져 두 채널 RRF(K=60)
  융합 top-k 근거 발췌를 되찾는다. 존재 노트만 위키링크(dangling 0). BM25 수식은 wiki-demo
  query.py에서 이식(ablation 검증 수식).
  - **wiki 운영 원칙**(gbrain·knowledge-manager 증류 — LLM-wiki 규칙):
    - **brain-first(C3)**: 질문을 받으면 외부 검색(웹·논문 DB) 전에 **내부 위키를 먼저**
      `wiki_query`로 검색한다 — 이미 검증해 쌓은 정본이 1차 출처다.
    - **컴파일 분리(B1)**: raw→wiki는 수집→보강→draft→lint→저장 단계를 분리한다.
      추출과 저장을 한 덩어리로 하지 않는다 — draft(40-drafts)를 거쳐 `wiki_promote` 게이트로만.
    - **추측 금지(E5)**: 노트 콘텐츠는 도구 응답(원문 실측·스크립트 출력)으로만 확정한다.
    - 노트는 Compiled Truth(현재값·REWRITE)+Timeline(append-only) 2분할 — 스키마는
      워크스페이스 `00-system/data-dictionary.md`.
  - **향후 확장(로드맵 — v0.3.0 미구현·stdlib 범위 밖)**: vector 임베딩 채널·시맨틱 캐시·
    토큰 예산 하드캡·GraphRAG(2-hop 라우팅)·cron 자율 정비·엣지 confidence decay.
- **지속 서베이**: arXiv 데일리가 같은 다이얼로 신착을 매칭하는 원리(스냅샷 ↔ 흐름).
- **다중 노드 협업**: roles.md의 master·worker·reviewer·inspector가 어떻게 심의하는지(대규모 서베이).

## §3.5 — 산출물 규약 (불변)
- **산출물은 사용자 워크스페이스의 `artifacts/` 또는 `40-drafts/`에만 쓴다.**
  - 워크스페이스(init으로 만든 10단위 구조)가 있으면: 작업 중 요약·초안은 `40-drafts/`,
    튜토리얼 대조표·기록물은 `artifacts/`(없으면 생성).
  - 워크스페이스 없이 튜토리얼만 진행 중이면: 현재 작업 폴더에 `artifacts/`를 만들어 그 안에만 쓴다.
  - **예외 — 현재 작업 폴더가 플러그인 폴더 안일 때**(clone 루트 또는 그 하위 폴더에서
    진행하는 세션 — 현재 폴더 **또는 상위 폴더 어디에든** `.claude-plugin/plugin.json`이
    보이면 이 경우다): 여기에 `artifacts/`를 만들면
    "플러그인 폴더에 쓰지 않는다" 규약과 충돌한다. 이때는 현재 폴더에 만들지 말고,
    **AskUserQuestion으로 산출 위치(사용자 폴더)를 물어** 지정받은 곳에 `artifacts/`를 만든다.
- **플러그인 폴더(`${CLAUDE_PLUGIN_ROOT}` 아래)에는 아무것도 쓰지 않는다** — 템플릿·references·
  examples는 읽기 전용 재료다. 슬롯 치환이 필요하면 사본을 산출 위치로 복사한 뒤 채운다.
- 이전 산출물은 삭제하지 않는다 — 정리가 필요하면 `artifacts/prev-<날짜>/`로 이동해 보존한다.

## §4 — 안전핀 (불변)
- 참고 코퍼스·원본 repo는 **읽기 전용**. 산출물은 §3.5 산출물 규약의 위치에만 쓴다.
- 정본(wiki) 직접 쓰기 금지 — 승격 게이트 경유만.
- 외부 발행(git push·메시지 발송·공개 배포)·비가역 삭제는 **사용자 승인 후에만**.
- 대화형 선택은 AskUserQuestion 툴 JSON으로. 각 단계는 질문으로 종료.

---

## 실측 → 규칙 승격 (리허설 각주)
> 이 대본의 규칙 다수는 실제 서베이(ICML2026 9카테고리)에서 역산됐다. 예:
> - "요약 전 PDF p.1 제목 대조" = 서브에이전트가 엉뚱한 PDF를 요약한 사고(61714)에서.
> - "본문 정본 채택+불일치 명기" = 초록↔본문 수치가 다른 논문(60729)에서.
> - "리뷰어 판정도 원문 실측이 최종심" = 리뷰어가 파일을 못 읽고 낸 무효 점수에서.
> 상세 사례는 `../examples/icml2026-worked-example.md` §사고 대응.
