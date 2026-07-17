# Private 레포 등록 명령 세트 (HanEol-Lee77)

> 로컬 준비는 완료 상태다: git init + 커밋(v0.1.0) 완료, author/repo 필드 = HanEol-Lee77,
> .gitignore(pyc·settings.local.json 제외) 적용, `claude plugin validate` ✔.
> 아래 **①②는 외부 발행(레포 생성·push)이라 오너가 직접 실행**한다. ③④는 설치·검증.

## 전제 (실측 확인됨)
- gh CLI 로그인: `HanEol-Lee77` · git 프로토콜 SSH · 토큰 스코프 `repo`(private 포함)
- SSH 키: `id_ed25519` 등 존재 → private 레포 clone/push 가능

## ① private 레포 생성 + push (한 방)
```powershell
cd C:\Users\deepnoid\gpters23\research-survey
gh repo create HanEol-Lee77/research-survey --private --source=. --remote=origin --push
```
분리 실행을 원하면:
```powershell
gh repo create HanEol-Lee77/research-survey --private
git remote add origin git@github.com:HanEol-Lee77/research-survey.git
git push -u origin main
```

## ② (선택) 릴리스 태그
```powershell
git tag research-survey--v0.1.0    # claude plugin tag 규약과 정합
git push origin research-survey--v0.1.0
```

## ③ private 레포를 마켓플레이스로 등록 + 설치
```powershell
# SSH url — 기존 SSH 키로 private clone
claude plugin marketplace add git@github.com:HanEol-Lee77/research-survey.git
#   (또는 짧게)  claude plugin marketplace add HanEol-Lee77/research-survey
claude plugin install research-survey@research-survey
```

## ④ 검증
```powershell
claude plugin list                 # research-survey  enabled 확인
claude plugin details research-survey
# Claude Code 재시작 후:
#   /research-survey tutorial       (또는 자연어: "연구 서베이 튜토리얼 시작")
```

## 이후 업데이트 (버전 올릴 때)
```powershell
# 변경 → CHANGELOG·plugin.json version 갱신 → 커밋 → push
git add -A && git commit -m "..." && git push
claude plugin update research-survey
```

---
### 참고 — 레포 없이 로컬만(가장 private, 이미 검증됨)
private 공유가 필요 없으면 레포 없이 로컬 디렉토리로 그대로 쓸 수 있다:
```powershell
claude plugin marketplace add C:\Users\deepnoid\gpters23\research-survey
claude plugin install research-survey@research-survey
```
