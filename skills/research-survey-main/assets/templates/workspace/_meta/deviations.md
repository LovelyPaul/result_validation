# 표준 이탈 기록 (deviations)

workspace-standards에서 벗어난 부분과 사유를 기록한다.

| 영역 | 변경 내용 | 사유 |
|---|---|---|
| CLAUDE.md 섹션 구성 | 표준 ①(제목+한 줄)을 H1으로 처리해 표준 ②~⑩이 `## 1`~`## 9`로 **1씩 앞당겨짐**. 표준 12섹션 목록(04-CLAUDE_MD_GUIDE.md) 밖의 `## 10. 도구 (결정론)` 삽입으로 표준 ⑪산출물 형식·⑫품질+이력은 `## 11`·`## 12`로 번호가 다시 일치 | 서베이 워크스페이스는 결정론 스크립트(classify/verify) 사용법이 핵심이라 별도 섹션이 필요 — 추가는 허용 범위, 번호 매핑 차이만 기록 |
| 자기소개 어댑터 `AGENTS.md` 추가 + CLAUDE.md 상단 `@AGENTS.md` import 1줄 | 워크스페이스 루트에 `AGENTS.md`(세션 시작 시 진행 상황 실측→다음 액션 제안하는 운영 에이전트 자기소개)를 신설하고, CLAUDE.md 최상단에 이를 가리키는 blockquote+`@AGENTS.md` import를 추가. **12섹션 본문·번호는 무손상**(import는 섹션 밖 최상단) | 하네스 7-layer의 instruction surface 확장 — repo-root CLAUDE.md=@AGENTS.md 패턴과 정합. init이 찍는 사용자 워크스페이스도 clone repo처럼 세션 시작 시 자기소개하게 하는 갭 해소(v0.7.1). 가장 덜 침습적(섹션 재번호 0) |
