# Worked Example — ICML 2026 서베이 (실제 사례)

> 이 플러그인의 파이프라인을 실제로 돌린 기록. 편수·판정·사고 대응이 전부 실측이다.
> 튜토리얼에서 코퍼스가 없을 때 이 예제를 낭독 모드로 진행할 수 있다.

## 코퍼스
- ICML 2026 승인논문 **6,628편**(제목·저자·초록·키워드 100%), PDF 6,627편(OpenReview 6,614 + arXiv 4,280).
- OpenReview API 직접 호출 403 → Firefox 실세션 쿠키 + curl_cffi JA3 임퍼스네이션 + 1워커/1.5초로 확보
  (고속 다워커는 Cloudflare 차단). **공식 인증·정식 경로만 사용.**

## 다이얼 → 추출 (9카테고리, 다중라벨)
| 카테고리 | 편수 | oral |
|---|---|---|
| llm-pretrain | 158 | 6 |
| llm-midtrain | 11 | 2 |
| llm-posttrain | 224 | 4 |
| data-synthesis | 19 | 0 |
| llm-eval | 191 | 6 |
| mllm-eval | 101 | 2 |
| vlm-token-compression | 17 | 0 |
| vlm-eval | 30 | 1 |
| medical-data-gen | 29 | 0 |

- oral 168편은 `_oral_list.html` 제목 정규화 exact 매칭(168/168).
- 다이얼 튜닝 실측: `medical-data-gen` guard가 처음엔 "patients?/diseases?"까지 포함 → 59편(비의료
  혼입) → guard를 의료영상/EHR 어휘로 조이고 noise_terms(protein·genomic) 추가 → **29편**. `data-synthesis`
  는 `guard: lm` 부여로 44→19편.

## 요약 + 3중 검증
- 쇼트리스트 상위 30(카테고리별) → **PDF 실측 요약 226편**(1차 28 + 2차 169 + medical 29).
- 3중 검증 전건 PASS: worker 결정론 자가검증 → master 독립 실측 → codex 표본 PDF 대조(6+12+4건).

## 정리
- Notion 200+페이지(카테고리 인덱스 9 · 인사이트 · 요약 226) — 툴 제한 대응(문단 1,900자·표 90행 분할).
- wiki 정본 `research/surveys/icml2026-multi-category.md` — cold-read 2라운드(REVISE→수정) 후 승격 게이트 통과.
- 지속: arXiv 데일리(cs.CL/CV/LG)를 같은 다이얼로 매칭 → 매일 다이제스트(첫 실측 236편 수집→12편 매칭).

## 가설 (idea-critic 게이트)
- vlm-token-compression 우선 4건 → R1·R2 전건 **hold**(reviewer novelty 2 = "초록 재조합").
- 1건(왜곡-제약 압축상한) 딥다이브 → 근거 논문 전문 3편 + novelty-critical 2편 정독 → 갭 좌표화
  ("seed-calibrated ε vs per-task oracle 전이검증 미확인") → novelty 2→3 회복. feasibility 3 캡 지속 →
  **문서로는 한계, cheap-kill 파일럿 실험이 유일 승격 경로**(리소스 결정). 전 판정은 ledger에 영속.

## ★사고 대응 — 규칙의 계보 (튜토리얼의 핵심 교훈)
1. **엉뚱한 논문 요약(61714)** — 병렬 서브에이전트가 다른 PDF를 읽어 오요약. 코퍼스는 정상. →
   "요약 착수 전 PDF p.1 제목 대조 + source_pdf 기록" 규칙 도입 → 이후 61638 실불일치 즉시 포착.
2. **camera-ready 개제(61638·66787)** — 제목 불일치 플래그 → 초록 축자 일치 + 동일 forum id 확인 →
   오매핑 아닌 개제로 판정 → "초록 일치+forum 일치=동일 논문" 자가판정 규칙화.
3. **초록↔본문 수치 불일치(60729)** — 리뷰어가 90.5%를 결함 지적 → master가 Table 1 실측 → 90.5%가
   정본(90.3%는 논문 초록/결론) → "본문 정본 채택+불일치 명기" + **리뷰어 판정도 원문 실측이 최종심**.
4. **검수 좌석 무효 판정** — codex가 파일을 못 읽고(샌드박스 오류) 1/1/1 → 무효 폐기·재실행 → "못 본
   채 점수 금지, 검증 불가=blocking 신고".
5. **외부 서비스 일괄 조작 사고** — 검색 기반 일괄 archive가 부분일치로 무관 페이지 25건 오조작 → 전량
   복구 → "외부 일괄 조작은 명시 ID 화이트리스트 + dry-run만".
6. **리뷰어 벤더 쿼터 소진** — 표본 검증을 다른 좌석(codex)으로 폴백 → 벤더 다양성 약화는 정직 라벨링.
7. **세션 한도 중단** — 재개 포인터(상태 저장) → 리셋 후 재-dispatch로 무손실 복구. 배치 축소로 완화.

## 재현 커맨드 (요약)
```
# 새 카테고리
taxonomy.json 편집 → 재분류 → --sample 표본검수 → 스켈레톤 → [요약 위임] →
3중 검증 → 정리 업로드 → 인사이트 → (선택)서베이 승격 → (선택)가설 채점
# 지속
매일 신착을 같은 다이얼로 매칭 → 다이제스트
```
전체 프로세스 상세는 프로젝트의 `DEV_TEAM_PLAYBOOK.md`(11단계·역할·통신·사고집) 참조.
