<!-- ev_type: clean-control -->
<!-- ev_expect: pass -->
## 변경 요지
verify_token에 만료 검사를 추가한다 (src/auth.py:42).

## 변경 근거
- coverage 91.2% 로 상승 (src/auth.py:42)
- "12 passed, 0 failed" 테스트 통과 (tests/test_auth.py:10)

## 리스크
TokenExpired 예외 처리 경로가 호출부에 전파되는지 확인 필요.

source_diff: PR#123.diff — PR#123
