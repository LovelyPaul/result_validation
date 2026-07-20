# phase_contracts — 서베이 11단계 계약

각 단계: **담당 · 입력 → 처리 → 출력 · 게이트**. (다중 노드 협업 시 담당은 roles.md 참조;
단독 실행이면 진행자 에이전트가 전 단계를 수행하되 검증 단계는 별도 서브에이전트/세션으로 분리.)

## 0. 코퍼스 확보 (선행)
- 입력: 관심 학회/소스. 처리: 제목·저자·초록·PDF 수집. 출력: `master.json`(불변 SOT) + PDF.
- 게이트: 초록 커버리지·PDF 보유율 실측 기록. (차단 사이트는 정식 인증/공식 경로만 — 규약 준수.)

## 1. 토픽 다이얼 정의/조정
- 입력: 관심 주제. 처리: `taxonomy.json`에 카테고리 추가(patterns/relevance_terms/noise_terms/guard/threshold).
- 출력: 다이얼. **이 파일 하나가 스냅샷 추출 + 지속 매칭을 동시 지배.**
- 게이트: 조정 전후 카운트 diff + 표본 5편 보고. 사유 1줄 기록. 상세: taxonomy_dial.md.

## 2. 결정론 분류
- 도구: 플러그인 동봉 `skills/research-survey-run/scripts/classify.py`(자립·표준 라이브러리).
- 입력: `00-system/taxonomy.json` + `60-data/corpus.json`(범용 스키마 — data-dictionary.md).
  학회 원본(예: ICML master.json)은 이 스키마로 매핑: `id=poster_id, url=논문링크, flags.oral=oral 여부,
  title/abstract/keywords 그대로`. 처리: 다중라벨 분류(title 가중·guard 배제·relevance+1·noise−2·랭킹).
- 출력: `70-analysis/{categories,shortlist,summary.md,all_categorized.json}`.
- 게이트: `classify.py --workspace . --sample <cat> N`(고정 시드) 표본 검수. LLM 재추론 금지(도구 출력만).

## 3. oral/중요도 병합 (해당 시)
- 입력: 학회 oral 목록. 처리: 제목 정규화 exact 매칭. 출력: oral 플래그(원본 불변 런타임 join).

## 4. 요약 스켈레톤 생성
- 입력: 쇼트리스트. 처리: 논문별 스켈레톤 md(Abstract·Meta·빈 Summary/Why/Evidence + PDF 경로).
- 출력: drafts/<cat>/<id>.md.

## 5. 요약 (위임)
- 입력: 스켈레톤 + PDF. 처리: **논문 1편당 서브에이전트 1개** 병렬 — PDF 전문 실측.
  각 요약: Summary(문제/방법/핵심결과/한계) · Why(연구 접점) · Evidence(수치 + `— Table X, p.Y`) ·
  `source_pdf: <파일> (p.1 제목 대조 OK)`.
- 게이트: 요약 착수 전 PDF p.1 제목 ↔ 스켈레톤 제목 대조. 불일치 = 요약 금지·플래그.

## 6. ★3중 검증 (producer≠evaluator)
1. 자가검증(결정론): `scripts/verify_summaries.py --dir 40-drafts/<cat>` — 플레이스홀더 0·섹션 완비·
   페이지인용 ≥3·source_pdf.
2. 독립 실측: 같은 스크립트를 만든이가 아닌 좌석/세션이 재실행.
3. 표본 원문 대조: 카테고리당 2편을 cold-read 좌석이 PDF와 대조(발명 수치·왜곡·페이지 오인용).
- 게이트: 3중 전부 PASS. 상충 시 원문 실측이 최종심. 상세: quality_gates.md.

## 7. 정리 (wiki 색인 / Notion·문서)
- 도구: 플러그인 동봉 `skills/research-survey-run/scripts/wiki_index.py`·`wiki_query.py`(자립·표준 라이브러리).
- 입력: 검증된 요약(정본 승격분). 처리: `wiki_index.py --workspace .`로 `20-knowledge-base/wiki/notes/`를
  검색 색인으로 빌드(FTS5 가용 시 FTS5+bm25(), 불가 시 순수 파이썬 문자 bigram BM25 폴백 — 실측 후 mode 명시),
  `wiki_query.py --workspace . "<질문>"`로 FTS5 매치 채널 + bigram BM25 채널을 RRF(K=60)로 융합한
  top-k 검색 리포트를 `wiki/queries/`에 생성(존재 노트만 위키링크 — dangling 0). 색인 시 링크 엣지
  자동 추출(zero-LLM)·orphan/broken 감사·델타 색인. Notion 등 외부 목적지는 선택(툴 제한 대응 — 분할 등).
- 출력: 검색 색인(`wiki/.index/` — wiki.db·edges.json·manifest.json) + 검색 리포트(`wiki/queries/`) + (선택) 외부 페이지·인덱스.
- 게이트: 미작성 스켈레톤 자동 skip. 외부 업로드 시 API 회독으로 카운트 대조. 일괄 조작은 명시 ID만.

## 8. 인사이트 추출
- 입력: 쇼트리스트 초록. 처리: 주제 클러스터·트렌드·연구 갭·가설 후보·(요청 시) 관심 초점 선별.
- 출력: INSIGHTS_<cat>.md.

## 9. 서베이 정본 승격 (게이트 경유)
- 도구: 플러그인 동봉 `skills/research-survey-run/scripts/wiki_promote.py`(자립·표준 라이브러리).
- 입력: 검증 통과 산출물(40-drafts 요약·80-reports 서베이). 처리: 서베이 초안 → cold-read 라운드
  (REVISE 반영) → `wiki_promote.py --workspace . <산출물.md>`로 승격. 기본 dry-run(diff 미리보기),
  `--apply`는 사람 승인 후에만. 노트 스키마 lint(frontmatter 필수키 `id/title/created/tags` + 출처 인용
  + Compiled Truth/Timeline 2분할)를 코드로 강제 — 미충족 시 승격 거부(garbage-in 차단). 갱신은
  Compiled Truth 교체 + Timeline append만(기존 Timeline 수정 감지 시 거부), 제목/ID dedup 내장.
- 출력: 정본 노트(`20-knowledge-base/wiki/notes/`) + 승격 이력 manifest(`wiki/promotion-manifest.jsonl`, JSONL append).
- 게이트: **정본 직접 쓰기 금지** — `wiki_promote`가 유일 통로. dry-run → 사람 승인 → `--apply`.

## 10. 가설 작성·심의
- 입력: 인사이트의 아이디어. 처리: falsifiable ic 초안 → 2좌석 채점(reviewer fact-verify +
  inspector leak-audit). 판정: accept_threshold 통과분만 승격, 미달은 hold + 사유·개정 트리거를 ledger에.
- 딥다이브: hold를 살리려면 배치 재생성이 아니라 **근거 논문 전문 정독**으로 갭 재정의.
  문서로 안 오르면(feasibility 캡) 파일럿 실험이 유일 경로(리소스 결정).

## 11. 지속 서베이
- arXiv 데일리: 신착을 **같은 다이얼**로 매칭 → 델타 적재(dedup). 새 카테고리 자동 상속.
- 다이제스트: 채널로 정기 발송(발송 dedup).
