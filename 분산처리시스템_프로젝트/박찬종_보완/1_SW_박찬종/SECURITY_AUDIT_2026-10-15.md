# 2차 보안 감사 — 보완본(패치 적용 후) 잔존 취약점

**감사일**: 2026-10-15
**대상**: `app/app.py` (363줄), `app/templates/`, `seed/seed_data.py`, `scripts/`, `config/`
**방법**: 코드 리뷰 + mongomock 기반 실제 실행 검증 (추정이 아니라 재현 결과)
**배경**: 2026-09-18 1차 감사에서 5건을 패치한 상태. 이 문서는 **패치 이후에도 남아 있는 것**을 다룬다.

> **이 문서는 2026-10-15 시점의 스냅샷이다.** 본문의 `app.py:119` 같은 줄 번호는
> **패치 전** 파일 기준이며, 이후 수정으로 현재 줄 번호와는 다르다.
> 조치 결과는 바로 아래 "조치 현황"을 참고할 것.
>
> 또한 애플리케이션 코드(`app.py` 등)는 **저장소에 포함되어 있지 않다**(`.gitignore`).
> 이 문서는 그 코드를 감사한 기록이며, 인용된 코드 조각으로 내용을 확인할 수 있다.

> 1차에서 고친 5건(인증 부재·role 자가상승·ReDoS·하드코딩 시크릿·예외 노출)은
> 재확인 결과 **정상적으로 패치되어 있다**. 아래는 그때 범위에 없었던 항목들이다.

---

## ⚠️ 조치 현황 (2026-10-16 갱신)

> **🔴 높음 3건(H-1·H-2·H-3)은 2026-10-16에 전부 패치했고 재검증까지 마쳤다.**
> 하드코딩된 데모 비밀번호도 `SEED_PASSWORD` 환경변수로 분리했다.
> **🟡 중간 5건과 🟢 낮음 5건은 여전히 열려 있다.**
> 패치 내용·검증 결과는 `README.md`의 "2차 보안 감사 및 패치" 절 참고.
>
> | 항목 | 상태 |
> | --- | --- |
> | H-1 오픈 리다이렉트 | ✅ 수정 (`_safe_next()`) — `302 → /` 확인 |
> | H-2 예약 IDOR | ✅ 수정 (세션 기반 명의) — 본인 ID로 기록됨 확인 |
> | H-3 빈 비밀번호 | ✅ 수정 (`_validate_new_user()`) — `400` 확인 |
> | M-1 ~ M-5, L-1 ~ L-5 | ❌ **미조치** |

## 요약 (최초 감사 시점)

| 심각도 | 건수 | 항목 | 조치 |
| --- | --- | --- | --- |
| 🔴 높음 | 3 | 오픈 리다이렉트 · 예약 IDOR · 빈 비밀번호 허용 | ✅ 전부 수정 |
| 🟡 중간 | 5 | CSRF 부재 · 이메일 중복 · `/health` 예외 노출 · 세션 쿠키 플래그 · 로그인 시도 제한 없음 | ❌ 미조치 |
| 🟢 낮음 | 5 | 이중예약 · 로그아웃 GET · CLI 비밀번호 노출 · 보안 헤더 · 시드 전체 삭제 | ❌ 미조치 |

**검증 방식**: 🔴·🟡 전 항목은 **추정이 아니라 실제로 실행해 재현**했다.
`USE_MONGOMOCK=1` 로 인메모리 DB를 띄우고 Flask `test_client()` 로 요청을 보내
응답 코드·`Location` 헤더·DB에 실제로 기록된 값을 확인하는 방식이다.
각 항목의 "재현 결과" 블록이 그 출력이며, 패치 후 **같은 절차를 다시 돌려**
결과가 뒤집히는 것까지 확인했다(아래 "조치 현황").

---

## 🔴 높음

### H-1. 오픈 리다이렉트 (Open Redirect) — `app.py:119`

```python
return redirect(request.args.get("next") or url_for("index"))
```

`next` 파라미터를 **검증 없이** `redirect()`에 넘긴다. `login_required`가 넣는 값은
`request.path`라 안전하지만, 공격자가 URL을 직접 만들면 외부 도메인으로 보낼 수 있다.

**재현 결과**
```
POST /login?next=https://evil.example.com/phish  (정상 자격증명)
→ 302  Location: https://evil.example.com/phish
```

**영향**: 피싱. 사용자는 **진짜 사내 로그인 페이지**에서 정상적으로 로그인했는데
공격자 사이트로 떨어진다. 도메인이 신뢰 도메인이라 링크 검사도 통과한다.

**수정 방향**: `next`가 `/`로 시작하고 `//`·`\\`로 시작하지 않는 **상대 경로일 때만** 허용.
```python
nxt = request.args.get("next", "")
if not (nxt.startswith("/") and not nxt.startswith("//")):
    nxt = url_for("index")
return redirect(nxt)
```

### H-2. 예약 생성 IDOR — `app.py:226`

```python
"user_id": ObjectId(f["user_id"]),   # ← 폼이 보낸 값을 그대로 신뢰
```

`login_required`는 "로그인했는가"만 확인하고, **"누구 명의로 예약하는가"는 검사하지 않는다.**
폼의 `user_id`를 바꾸면 임의의 타인 명의로 예약이 생성된다.

**재현 결과**
```
로그인 사용자 = 홍길동(…2ef6)
POST /reservations/new  user_id=…2ef5 (관리자)
→ DB에 기록된 user_id = …2ef5   (관리자 명의로 생성됨)
```

**영향**: 타인 사칭 예약, 책임 추적 불가. 예약 취소·변경 기능이 추가되면
**타인 예약 조작**으로 바로 확대된다.

**수정 방향**: 폼의 `user_id`를 받지 말고 `session["user_id"]`를 쓸 것.
관리자가 대리 예약해야 한다면 그 경로만 `admin_required`로 분리.

### H-3. 빈 비밀번호 계정 생성·로그인 허용 — `app.py:278`

```python
raw_pw = data.get("password", "")      # 빈 문자열 기본값
pw_hash = bcrypt.hashpw(raw_pw.encode("utf-8"), bcrypt.gensalt())
```

비밀번호 존재·길이·복잡도 검증이 없다. **빈 문자열도 그대로 해싱되어 저장**되고,
로그인 시 `bcrypt.checkpw(b"", hash)`가 참이 되어 통과한다.

**재현 결과**
```
POST /api/users {"email":"empty@example.com","password":""}  → 201 Created
POST /login     email=empty@example.com, password=(빈 값)    → 302 Location: /   (로그인 성공)
```

**영향**: 관리자가 비밀번호 필드를 빠뜨리면 **누구나 그 계정으로 로그인 가능한 계정**이 조용히 생성된다.
`role`을 `admin`으로 함께 보내면 비밀번호 없는 관리자 계정이 된다.

**수정 방향**: 최소 길이(예: 10자)·공백 불가 검증 후 거부(400). `email` 형식 검증도 함께.

---

## 🟡 중간

### M-1. CSRF 방어 전무

세 개 폼(`/login`, `/reservations/new`, `/rooms` 검색) 어디에도 CSRF 토큰이 없고,
`flask-wtf`/`CSRFProtect`도 쓰지 않는다. **재현 결과**: 예약 폼 HTML에 `csrf` 문자열 0건.

현재는 브라우저 기본값(`SameSite=Lax`)이 교차 사이트 POST를 막아주지만,
이는 **애플리케이션의 방어가 아니라 브라우저에 기댄 것**이다 (M-4 참고).

**수정 방향**: `CSRFProtect(app)` 적용 + 템플릿에 `{{ csrf_token() }}`.

### M-2. 이메일 중복 허용 — 유니크 인덱스 없음

**재현 결과**: 같은 이메일로 두 번 생성 → 문서 2건.
로그인은 `find_one`이라 **둘 중 하나만** 매칭된다. 비밀번호를 바꿨다고 생각해도
다른 문서가 남아 **옛 비밀번호로 계속 로그인**될 수 있다.

**수정 방향**: `db.users.create_index("email", unique=True)` + 생성 시 중복 검사.

### M-3. `/health` 인증 없음 + 예외 메시지 노출 — `app.py:260`

```python
return jsonify({"status": "error", "message": str(e)}), 500
```

1차 감사에서 `/reservations/new`의 `str(e)` 노출은 고쳤지만 **`/health`에는 같은 패턴이 남아 있다.**
pymongo 예외 메시지에는 **replica set 호스트·포트 목록**이 포함된다.
또한 `/health`는 비로그인 상태에서 200을 반환해 **노드 역할(`is_primary`)이 외부에 공개**된다.

**재현 결과**: 비로그인 `GET /health` → `200 {"is_primary":null,"status":"ok"}`

**수정 방향**: 예외는 로그로만, 응답은 일반 메시지. 상세 상태는 `login_required`(또는 `admin_required`) 뒤로.

### M-4. 세션 쿠키 보안 플래그 미설정

**재현 결과**
| 설정 | 현재 값 | 문제 |
| --- | --- | --- |
| `SESSION_COOKIE_SECURE` | `False` | **HTTP 평문으로도 쿠키 전송** |
| `SESSION_COOKIE_HTTPONLY` | `True` | 정상 (Flask 기본값) |
| `SESSION_COOKIE_SAMESITE` | 미설정 | 브라우저 기본(Lax)에 의존 |

이 앱은 TLS 없이 HTTP로 뜬다(Tailscale 터널이 전송 암호화를 담당). 터널 밖/내부
동일 호스트 관점에서는 **세션 쿠키가 평문**이다.

**수정 방향**: `app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE="Lax")`.

### M-5. 로그인 시도 제한 없음 + 타이밍 기반 계정 열거

**재현 결과 (중앙값, 12회)**
| 입력 | 응답 시간 |
| --- | --- |
| 존재하는 이메일 + 틀린 비밀번호 | **165.4 ms** |
| 없는 이메일 + 틀린 비밀번호 | **0.6 ms** |

차이 **약 165ms**. 계정이 없으면 `bcrypt.checkpw`를 아예 호출하지 않아 즉시 반환된다.
→ **어떤 이메일이 등록돼 있는지 외부에서 판별 가능**.

또한 rate limit·계정 잠금 코드가 전혀 없다(식별자 검색 0건). bcrypt가 느려
초당 시도 수는 제한되지만, **무제한 시도 자체는 가능**하다.

**수정 방향**: 사용자가 없을 때도 더미 해시로 `checkpw`를 돌려 시간을 맞추고,
`flask-limiter`로 IP·계정당 시도 제한.

---

## 🟢 낮음

| # | 항목 | 내용 |
| --- | --- | --- |
| L-1 | **이중 예약 허용** | 같은 회의실·같은 시간대 예약이 2건 생성됨(재현). 보안보다 업무 로직 결함이지만, 예약 시스템의 핵심 기능이 빠져 있다 |
| L-2 | **`/logout`이 GET** | 외부 사이트의 `<img src=".../logout">` 한 줄로 강제 로그아웃 가능(경미). POST + CSRF 토큰 권장 |
| L-3 | **CLI 인자로 비밀번호 전달** | `05_failover_test.sh`·`06_replication_test.sh`가 `-u … -p ${PWD}` 형태로 넘긴다. 같은 호스트의 다른 사용자가 `ps`로 볼 수 있다. 환경변수/`--authenticationDatabase` + stdin 권장 |
| L-4 | **보안 헤더 미설정** | CSP·X-Frame-Options·HSTS 없음(식별자 검색 0건). 클릭재킹 방어 없음 |
| L-5 | **시드가 전체 삭제 후 삽입** | `seed_data.py`가 확인 없이 `users`/`rooms`를 `delete_many({})` 한다. 운영 DB에 실수로 돌리면 전체 소실 |

### 참고 — 안전하다고 확인한 것

- **XSS**: 템플릿에 `|safe`·`autoescape false` 0건 → Jinja 자동 이스케이프 정상 동작
- **NoSQL 인젝션(로그인)**: 이메일이 폼 데이터(항상 문자열)라 연산자 주입 불가
- **ReDoS**: `re.escape()` + 100자 제한 패치가 그대로 유지됨
- **role 자가상승**: `ALLOWED_ROLES` 화이트리스트 + `admin_required` 이중 방어 유지
- **하드코딩 크리덴셜**: `cluster.env`·`.env.example` 모두 `CHANGE_ME` 플레이스홀더 상태
- **`debug=False`**, bind 기본값 `127.0.0.1` — 둘 다 안전한 기본값
- **keyFile**: `openssl rand -base64 756` + `chmod 400` + `chown mongodb` 정상

---

## 권고 순서

1. **H-1, H-2, H-3** — 코드 몇 줄로 고칠 수 있고 영향이 가장 크다
2. **M-2, M-3** — 유니크 인덱스 추가, `/health` 예외·노출 정리
3. **M-1, M-4** — `CSRFProtect` + 쿠키 플래그 (함께 처리하면 효율적)
4. **M-5** — 더미 해시로 타이밍 평탄화, rate limit 도입
5. **L-1** — 이중예약 차단은 보안이 아니라 기능 완성도 문제
6. **L-2 ~ L-5** — 운영 전 체크리스트로

**공개 전 판단**: H-1·H-2·H-3은 공개 저장소에 올리기 전에 고치는 것을 권한다.
세 건 모두 코드를 읽으면 바로 보이는 패턴이라, 공개 시 그대로 지적받을 가능성이 높다.
