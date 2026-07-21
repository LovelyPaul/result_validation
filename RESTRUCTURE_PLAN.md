# RESTRUCTURE_PLAN — research-survey v0.6.0 repo 구조 개편안 (승인·집행 완료)

> 상태: **옵션1 승인·집행 완료(2026-07-21)**. 기준 HEAD: `50aae98` (main).
> master 판정: (1)옵션1 채택 (2)INSTALL_MARKETPLACE→docs/ 승인 (3)README scripts 그룹표 포함
> (team_compare 예약 행). **물리 분리(옵션2)는 스크립트 증가 시 차기 메이저 재검토 항목으로 보존**(아래 §2 옵션2·§6).
> 목적(오너): scripts가 한 스킬 하위에 집중·문서류 산개·PRIVATE_REPO_SETUP 용도 소멸(공개 전환)을
> 정리하되, **비가역 삭제 없이(아카이브 이동)·하위호환·무파손**으로 개편한다.

---

## 1. 현황 진단 (실측)

### 1-A. 루트 파일 (8개)
| 파일 | 크기 | 판정 |
|---|---|---|
| README.md / README.ko.md | 7.1K / 7.6K | 유지(루트 정본) |
| CHANGELOG.md | 24K | 유지(append-only 이력 — 과거 서술 문구는 재작성 금지) |
| AGENTS.md / CLAUDE.md | 2.1K / 0K(=@AGENTS.md 포인터) | 유지(루트 어댑터 — plugin 규약 아니지만 clone 사용 경로) |
| INSTALL_MARKETPLACE.md | 2.5K | **이동 후보** → `docs/` (설치 안내·현행 유효) |
| PRIVATE_REPO_SETUP.md | 2.2K | **아카이브 이동** → `docs/archive/` (공개 전환으로 용도 소멸·비가역 삭제 회피) |

### 1-B. scripts 7종 (전부 `skills/research-survey-run/scripts/`)
| 스크립트 | 크기 | 기능군 | self-test |
|---|---|---|---|
| wiki_index.py | 24.4K | **wiki** (색인·감사·타입드 엣지) | ✔ |
| wiki_query.py | 12.7K | **wiki** (RRF 검색) | ✔ |
| wiki_promote.py | 17.0K | **wiki** (승격 게이트) | ✔ |
| wiki_grade.py | 19.5K | **wiki** (평가 하네스) | ✔ |
| classify.py | 7.4K | **corpus** (분류·랭킹) | (—) |
| corpus_fetch.py | 19.2K | **corpus** (arXiv 반입·델타) | ✔ |
| verify_summaries.py | 20.6K | **verify** (검수·source-coverage) | ✔ |

### 1-C. ★상호 import 결합 (개편 핵심 제약 — 물리 이동의 최대 리스크)
스크립트들은 `sys.path.insert(0, str(Path(__file__).resolve().parent))` 후 형제 모듈을
import한다. **같은 디렉터리에 있다는 가정에 의존**한다:
- `wiki_query.py:37` → `from wiki_index import REQUIRED_KEYS, load_notes`
- `wiki_grade.py:36-38` → `from wiki_query import ...` / `from wiki_promote import ...` /
  `from verify_summaries import resolve_source, check_evidence_grounding`

즉 **wiki_grade(wiki군)가 verify_summaries(verify군)를 import**한다 — 기능군을 물리적으로
다른 폴더로 쪼개면 이 교차 import가 깨진다. 이동 시 sys.path 부트스트랩을 반드시 함께 갱신해야 한다.

### 1-D. 경로 참조 전수 (문서가 `skills/research-survey-run/scripts/…`를 가리키는 지점)
| 파일 | 줄 | 참조 스크립트 |
|---|---|---|
| `skills/research-survey-run/SKILL.md` | 13, 14, 25 | classify, verify_summaries |
| `skills/research-survey-main/references/phase_contracts.md` | 16, 37, 44, 58 | classify, verify, wiki_index/query, wiki_promote |
| `skills/research-survey-main/references/DEMO.md` | 40, 47, 48, 76 | classify, wiki_index, wiki_query, wiki_grade |
| `skills/research-survey-main/references/RUNBOOK.md` | 50, 211, 212, 228, 230, 269, 275 | classify, verify, corpus_fetch, wiki_grade, wiki_index |
| `assets/templates/workspace/CLAUDE.md` | 60 | scripts 폴더 총칭 |
| `commands/research-survey.md` | (scripts 직접 참조 없음 — skills 경로만) | — |
| `CHANGELOG.md` | 107, 125, 254 | **이력 서술 — 재작성 금지**(당시 사실) |

**README 2종**: 스크립트를 **이름으로만** 참조(`corpus_fetch.py` 등) — 경로 접두 없음 →
스크립트 파일명이 안 바뀌면 **영향 없음**.

### 1-E. plugin 스펙 불변 제약
- `.claude-plugin/{plugin.json, marketplace.json}` 위치 고정.
- `commands/<cmd>.md` 위치 고정.
- `skills/<skill-name>/SKILL.md` 위치·이름 고정(스킬 3종: -init/-main/-run).
- 스킬 하위 자산(references/·assets/·examples/·scripts/)은 `${CLAUDE_PLUGIN_ROOT}` 상대 참조라
  **플러그인 내부에서는 이동 가능** — 단 참조 전수 갱신 필수.

---

## 2. 개편안 (두 옵션 · 권고 포함)

### 옵션 1 — 문서 정돈 + 스크립트 논리 구획 (권고 · 최저 리스크)
스크립트는 **제자리(플랫) 유지**하고, 문서류만 정돈한다. 기능군은 물리 폴더가 아니라
**docstring 그룹 헤더 + SKILL/README의 그룹 표**로 구획한다.

```
research-survey/
  README.md · README.ko.md · CHANGELOG.md · AGENTS.md · CLAUDE.md
  docs/
    INSTALL_MARKETPLACE.md            # 루트 → docs/ 이동
    archive/
      PRIVATE_REPO_SETUP.md           # 용도 소멸 → 아카이브(비가역 삭제 회피)
  .claude-plugin/{plugin.json, marketplace.json}
  commands/research-survey.md
  skills/
    research-survey-init/SKILL.md
    research-survey-main/{SKILL.md, references/, assets/, examples/}
    research-survey-run/
      SKILL.md
      scripts/                        # 7종 제자리 — sys.path 결합 무손상
        (wiki) wiki_index · wiki_query · wiki_promote · wiki_grade
        (corpus) classify · corpus_fetch
        (verify) verify_summaries
```
- **이동**: `INSTALL_MARKETPLACE.md`→`docs/`, `PRIVATE_REPO_SETUP.md`→`docs/archive/` (2건).
- **참조 갱신**: INSTALL_MARKETPLACE를 가리키는 CHANGELOG는 이력이라 불변 → 실질 갱신 대상 0.
  (INSTALL_MARKETPLACE는 문서 본문에서 링크로 참조되지 않음 — README에 경로 링크 없음 확인.)
- **scripts 참조 갱신**: 0 (이동 안 함).
- **리스크**: 최저. import·경로 참조 churn 0. 무파손 증명이 단순.
- **한계**: "기능군 물리 분리"는 못 함(논리 구획만). 오너 목적의 "정리"는 문서·docstring 수준.

### 옵션 2 — 기능군 물리 분리 (오너 문구 직해 · 중간 리스크)
```
    research-survey-run/
      SKILL.md
      scripts/
        wiki/    wiki_index · wiki_query · wiki_promote · wiki_grade
        corpus/  classify · corpus_fetch
        verify/  verify_summaries
        _bootstrap.py            # 공유 sys.path 등록(3개 그룹 dir 전부 등록)
```
- **필수 코드 변경**: 각 스크립트 상단 `sys.path.insert` 를 3개 그룹 dir 모두 등록하도록 교체
  (wiki_grade→verify 교차 import 유지). 교차 import 경로 검증 필수.
- **참조 갱신**: §1-D의 문서 5개(SKILL/phase_contracts/DEMO/RUNBOOK/템플릿 CLAUDE) 전 줄 +
  경로에 `wiki/`·`corpus/`·`verify/` 삽입. CHANGELOG 이력은 불변.
- **리스크**: 중간. sys.path·교차 import·문서 20여 줄 갱신 → self-test/E2E로 전수 검증 필요.
- **이점**: 트리에서 기능군이 한눈에. scripts 성장 시 확장성.

### 권고
**옵션 1 채택**을 권고한다. 근거: (a)scripts 상호 import 결합이 강해 물리 분리는 순이익 대비
파손 리스크가 크다(품질 절대우선·무파손 요구), (b)오너 목적의 핵심(문서 산개·PRIVATE_REPO
용도 소멸)은 옵션 1로 완결된다, (c)"기능군 정리"는 docstring 그룹 헤더+SKILL 그룹 표로 가독성
목적을 달성한다, (d)7종이 성장 폭주 상태가 아니라 물리 분리의 시급성이 낮다.
옵션 2를 원하면 승인 시 명시해 달라 — sys.path 부트스트랩·참조 전수 갱신까지 포함해 집행한다.

---

## 3. 집행 순서 (승인 후 · 옵션 1 기준)
1. `docs/`·`docs/archive/` 생성, `git mv` 로 2개 파일 이동(이력 보존).
2. scripts docstring에 그룹 헤더 1줄 주석 부여(wiki/corpus/verify) — 동작 무변경.
3. `research-survey-run/SKILL.md`·README 2종에 scripts 기능군 그룹 표 1개 추가(선택·가독성).
4. **검증(무파손 증명)**: self-test 6종 exit0 + 데모 코어 E2E(classify→index→query→promote→
   재검색) + grade E2E(적중률·거부율) + `claude plugin validate` exit0.
5. 0.6.0 버전 3처·CHANGELOG에 개편 매핑 절 추가.
6. P0 로컬 커밋(push 금지).

## 4. 하위호환·안전
- 비가역 삭제 0 (PRIVATE_REPO_SETUP은 아카이브 이동).
- `git mv`로 이력 연속성 보존.
- 옵션 1은 스크립트 경로·이름 불변 → 기존 워크스페이스·문서 muscle memory 무손상.
- 롤백: 이동 2건 되돌리기만으로 원복(커밋 분리).

## 5. 승인 결과 (master 판정 2026-07-21)
- [x] 옵션 1(권고) 채택 — import 결합 실측 하 물리 분리는 순이익<파손리스크
- [x] `INSTALL_MARKETPLACE.md`→`docs/` 이동 승인 (링크 참조 전수 스캔: 실참조 CHANGELOG:91 이력뿐·라이브 링크 0)
- [x] README 2종에 scripts 기능군 그룹표 포함 (team_compare.py 예약 행 포함)

## 6. 차기 메이저 재검토 (deferred)
옵션2(scripts/{wiki,corpus,verify}/ 물리 분리 + `_bootstrap.py` sys.path 3군 등록)는 **스크립트
수가 더 늘어 플랫 디렉터리 가독성이 한계에 달할 때** 차기 메이저에서 재검토한다. 집행 시
§1-C 교차 import(wiki_grade→verify_summaries)와 §1-D 문서 참조 전수 갱신이 선행 조건이다.
