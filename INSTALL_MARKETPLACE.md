# 마켓플레이스 등록 안내 (오너 수동 단계)

이 플러그인(`research-survey`)을 gptaku-plugins 마켓플레이스에 올리려면 아래 2곳에 항목을 추가하고
독립 레포로 push해야 한다. **git push·서브모듈 추가는 외부 발행(비가역)이라 오너가 직접 수행** —
아래는 붙여넣을 스니펫이다.

## 1) `gptaku_plugins-main/.claude-plugin/marketplace.json` 의 `plugins[]`에 추가
```json
{
  "name": "research-survey",
  "description": "관심 연구 주제로 논문을 추출→요약→3중검증→인사이트·가설·서베이로 정리하는 지속 서베이 튜토리얼",
  "source": "./plugins/research-survey",
  "category": "education",
  "tags": ["research", "survey", "literature-review", "arxiv", "taxonomy", "tutorial"]
}
```

## 2) `gptaku_plugins-main/.gitmodules` 에 서브모듈 추가
```
[submodule "plugins/research-survey"]
	path = plugins/research-survey
	url = https://github.com/deepnoid/research-survey
```
(url은 실제 생성할 레포 주소로 교체.)

## 3) 독립 레포 생성·push (오너)
```
cd C:\Users\deepnoid\gpters23\research-survey
git init && git add . && git commit -m "feat: research-survey plugin v0.1.0"
# GitHub에 research-survey 레포 생성 후:
git remote add origin <repo-url> && git push -u origin main
# 마켓플레이스 레포에서:
git submodule add <repo-url> plugins/research-survey
```

## 로컬 테스트 (push 없이)
```
/plugin marketplace add C:\Users\deepnoid\gpters23\research-survey
/plugin install research-survey
# 재시작 후 /research-survey tutorial
```
> 참고: 단일 플러그인 폴더를 직접 marketplace로 add하려면 `.claude-plugin/plugin.json`만으로 충분
> (marketplace.json은 다중 플러그인 인덱스용). 로컬 검증은 이 방식이 가장 빠르다.

## 설치 문제 해결 (필드 테스트 실측 — 2026-07-21)

- **원격 add가 clone 타임아웃으로 실패하면**: repo가 **비공개일 가능성**을 먼저 확인하라 — GitHub는
  비인증 사용자에게 비공개 repo를 404로 응답하고, git은 자격증명 대기로 hang한다. 타임아웃을
  늘리기 전에 브라우저에서 repo URL 접근을 확인하고, 안 되면 **로컬 경로 add로 폴백**한다.
- **업데이트는 `name@marketplace` 형식**: `claude plugin update research-survey@research-survey` —
  이름 단독(`update research-survey`)은 "not found"로 실패한다(실측).
- Windows에서 install이 `EBUSY`(파일 잠금)로 간헐 실패하면 그대로 한 번 재시도하면 된다(실측).
