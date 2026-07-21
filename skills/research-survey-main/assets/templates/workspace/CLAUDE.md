# <프로젝트명> — 연구 서베이 워크스페이스

한 줄 설명: 관심 연구 주제로 논문을 지속 서베이하는 전용 워크스페이스(One Workspace, One Agent).

> **세션 시작 안내는 [@AGENTS.md](./AGENTS.md)를 따른다** — 구체 작업 지시 없이 이 워크스페이스를
> 열었을 때 진행 상황(PROJECT_STATUS·run-state)을 실측해 다음 액션을 제안하는 운영 에이전트
> 자기소개다. 아래 12섹션은 운영 규약 정본이며 그대로 유지된다.

@AGENTS.md

## 1. 대상 런타임
Claude Code (+ `research-survey` 플러그인). 분류·검수 스크립트는 python3(표준 라이브러리)만 요구.

## 2. ⚠️ 정체성 (허용/금지)
- **허용**: 관심 주제 논문 추출·요약·검증·인사이트·가설·서베이 정리·지속 추적.
- **금지**: 정본 직접 수정 · 출처 없는 데이터 · 검증 없는 인용 · 외부 발행(사용자 승인 없이).

## 3. 핵심 원칙
| # | 원칙 |
|---|---|
| 1 | 증거 기반 완료 — 출력·인용·검증만이 완료 |
| 2 | producer ≠ evaluator — 만든 좌석은 채점 안 함 |
| 3 | 환각 0 — 출처만이 사실, 모르면 물러남 |
| 4 | 축적 — 살아남는 아티팩트를 남김 |
| 5 | 결정론 환원 — 카운트·게이트는 스크립트로만 |

## 4. 폴더 구조
```
00-system/        방법론·데이터 딕셔너리·인용 스타일·taxonomy 다이얼
10-planning/      research-plan·hypothesis·timeline
20-knowledge-base/ 01_literature-review·references
30-templates/     TEMPLATE_* (요약·서베이·대조표)
40-drafts/        작업 중 요약 초안
50-output/        완성 산출물
60-data/          corpus.json(범용 스키마) · raw/ · processed/
70-analysis/      분류 결과(categories·shortlist·summary)·인사이트
80-reports/       interim/ final/ (서베이·가설)
90-archive/       보관
_meta/            deviations.md (표준 이탈 기록)
.claude/          commands·agents·skills·settings.local.json(로컬·gitignore)
```

## 5. 워크플로우
```
다이얼(00-system) → 추출(70-analysis) → 요약(40-drafts) → 3중 검증 →
정리(50-output/80-reports) → 가설(10-planning/80-reports) → 지속(arXiv)
```

## 6. 커맨드 (Scale Mode)
| 커맨드 | 모드 | 설명 |
|---|---|---|
| `/research-survey tutorial` | Lite(15분) | 파이프라인 라이브 튜토리얼 |
| `/research-survey run <cat>` | Standard(30분+) | 한 카테고리 1사이클 |

## 7. Scale Modes
- Lite: 시연·학습(한 사례 통쏘기). Standard: 한 카테고리 전체. Full: 다중 카테고리 + 지속 서베이 배선.

## 8. 트리거 경계
- should: 논문 서베이·문헌 정리·리서치 토픽 추적. NOT: 단발 웹 리서치(→deep-research)·PRD(→show-me-the-prd).

## 9. 도메인 프레임워크
- taxonomy 다이얼 · 3중 검증 · idea-critic 게이트 · 출처 등급(A~F)·삼각검증. 상세는 플러그인 references/.

## 10. 도구 (결정론)
- 분류: `classify.py --workspace .` (00-system/taxonomy.json + 60-data/corpus.json → 70-analysis/).
- 검수: `verify_summaries.py --dir 40-drafts/<cat>`. 둘 다 플러그인 `skills/research-survey-run/scripts/`.
- wiki 색인: `wiki_index.py --workspace .` (20-knowledge-base/wiki/notes/*.md → FTS5 색인 또는 python 폴백).
- wiki 검색: `wiki_query.py --workspace . "<질문>"` (FTS5 매치 + 문자 bigram BM25 유니온 → wiki/queries/ 리포트).
- wiki 승격: `wiki_promote.py --workspace . <산출물.md>` (기본 dry-run diff, `--apply`는 승인 후 — 정본 직접 쓰기 금지 게이트).

## 11. 산출물 형식
- 요약: Summary 4절 + Evidence 페이지 인용 + source_pdf. 서베이: 증분 문헌 지도(Delta Log). 대조표: 자립형 HTML.

## 12. 품질 규칙 + 변경 이력
- 출처 없는 데이터 금지 · 원본 직접 수정 금지 · 검증 없는 인용 금지. 변경은 CHANGELOG.md에 기록.
