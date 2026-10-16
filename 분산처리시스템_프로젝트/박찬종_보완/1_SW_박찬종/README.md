# 분산 DB 회의실 예약 시스템 — 인프라/보안 패키지 (1단계)

물리 PC 2대 + Tailscale 환경에서 **보안이 적용된 MongoDB Replica Set**을 구성하기 위한
설정·스크립트 묶음입니다. (요구사항 1·3·4·5 + 통신 보안 담당)

## 아키텍처

```
            [사용자 브라우저]
                  │ (Tailscale, 5000)
                  ▼
  ┌───────────────────────────┐        ┌───────────────────────────┐
  │  PC1 (Leader / 우선 Primary)│        │  PC2 (Follower)           │
  │  - mongod  :27017 (priority2)│◀──────▶│  - mongod  :27017 (priority1)│
  │  - Elasticsearch :9200      │ 복제   │  - mongod  :27018 (Arbiter) │
  │  - Flask 웹앱 :5000          │ (oplog)│  - Elasticsearch :9200      │
  └───────────────────────────┘        └───────────────────────────┘
        모든 노드 간 통신 = Tailscale(WireGuard) 암호화 터널
```

## 왜 Arbiter가 필요한가 (SDD용 핵심 설명)
Replica Set은 과반수 투표로 Primary를 뽑습니다. 데이터 노드가 2개뿐이면 majority=2라,
Leader 하나만 죽어도 남은 1표로는 과반 미달 → **자동 failover 불가**.
PC2에 데이터를 갖지 않는 **Arbiter(27018)** 를 1개 추가하면, PC1을 죽여도
`PC2데이터(1)+Arbiter(1)=2=과반` 이 되어 **PC2가 새 Primary로 승격**됩니다.
(주의: Arbiter를 데이터 노드와 같은 호스트에 두는 것은 학습/데모용 절충안이며,
운영 환경에서는 독립 호스트 권장 — 이 트레이드오프를 SDD에 명시하면 좋습니다.)

## 보안 계층 (요청하신 "통신 보안" — STR 보안 시험 항목으로 직결)
1. **네트워크 노출 차단**: mongod `bindIp` = loopback + Tailscale IP 만. 공인망 노출 0.
2. **방화벽(ufw)**: 27017/27018/9200 은 `tailscale0` 인터페이스 유입만 허용.
3. **Tailscale ACL**: `tag:meetingdb` 두 노드끼리만 해당 포트 통신 허용.
4. **멤버 내부 인증**: 동일 `keyFile` 로 Replica Set 멤버 인증.
5. **클라이언트 인증(SCRAM)**: `admin`(root) + `meeting_app`(readWrite, 최소권한) 분리.
6. **전송 암호화**: 모든 노드 간 트래픽이 Tailscale WireGuard 터널로 암호화.
   (추가 강화가 필요하면 mongod TLS를 옵션으로 적용 가능 — 요청 시 제공)

## 애플리케이션 계층 보안 검증 및 패치 (2026-09-18)

위 "보안 계층"은 전부 **네트워크/DB 계층** 얘기다. `app.py`(Flask)는 별도로 코드를 읽어
직접 검증했고, 실제로 구멍이 있었다 — Tailscale ACL·ufw가 잘 짜여 있어도 애플리케이션
자체에 방어선이 없으면 그 ACL 하나가 유일한 방어막이 된다.

| # | 심각도 | 문제 | 패치 |
| --- | --- | --- | --- |
| 1 | 높음 | `password_hash`를 저장만 하고 검증하는 로그인 라우트가 없었음 — 인증 자체가 존재하지 않아 Flask 포트에 닿으면 누구나 전체 사용자/예약 데이터를 보고 새 예약을 생성할 수 있었음 | `/login`(bcrypt.checkpw 검증) + 세션 발급, `login_required` 데코레이터로 모든 화면·API를 로그인 필수로 전환 |
| 2 | 높음 | `POST /api/users`가 클라이언트가 보낸 `role`을 그대로 저장 — 지금은 role을 쓰는 분기가 없어 당장은 무해하지만, role 기반 기능이 추가되는 순간 누구나 `role: "admin"`을 자가발급할 수 있는 구멍이었음 | `admin_required`로 API 자체를 관리자 전용으로 제한 + `ALLOWED_ROLES` 화이트리스트로 임의 문자열을 `user`로 강등(이중 방어) |
| 3 | 중간 | 회의실 검색 `q`가 이스케이프 없이 MongoDB `$regex`에 그대로 들어감 — 악의적으로 조작한 정규식으로 DB CPU를 고갈시키는 ReDoS 가능 | `re.escape(q)` 적용(항상 "부분 문자열 포함" 검색으로 동작, 기능은 동일) + 검색어 100자 상한 |
| 4 | 낮음 | `FLASK_SECRET` 기본값이 소스에 고정 문자열로 하드코딩 — 환경변수를 안 채우면 이제 공개 저장소에 실릴 값으로 세션이 서명됨 | 미설정 시 매 기동마다 `secrets.token_hex(32)`로 무작위 키 생성(재시작 시 세션 무효화는 감수) + 콘솔 경고 출력 |
| 5 | 낮음 | 예약 생성 실패 시 `str(e)`(내부 예외 메시지)를 그대로 사용자에게 flash로 노출 | 서버 로그(`app.logger.exception`)에만 남기고 사용자에게는 일반 메시지만 표시 |

**확인해서 안전하다고 판단한 것**: 템플릿 어디에도 `|safe` 필터가 없어 Jinja 자동
이스케이프가 살아있음 — 저장형 XSS는 이 경로로는 성립하지 않는다.

**mongomock 기반 스모크 테스트로 검증**(`test_app_security.py`, 로컬 임시 실행 — 저장소에는
포함하지 않음): 비로그인 접근 시 리다이렉트, 잘못된 비밀번호 거부, 정상 로그인/로그아웃,
비관리자의 `/api/users` 거부, 관리자 호출에서도 화이트리스트 밖 role 강등, 악성 정규식
검색어가 예외 없이 빈 결과로 처리되는 것까지 11개 항목 전부 통과.

로그인 화면은 `seed_data.py`가 만든 계정으로 테스트할 수 있다 — `admin@example.com`이
`role: admin`이다. **비밀번호는 소스에 하드코딩하지 않는다**(아래 2차 감사 §C 참고):
`SEED_PASSWORD` 환경변수로 주입하거나, 미설정 시 시드 실행 때 무작위 생성되어
콘솔에 1회만 출력된다.

```bash
SEED_PASSWORD='원하는_강한_비밀번호' MONGO_URI="..." python3 seed/seed_data.py
```

## 2차 보안 감사 및 패치 (2026-10-16)

1차 패치 이후 **같은 코드를 다시 감사**했다. 1차에서 고친 5건은 정상 유지되고 있었고,
그때 범위에 없던 **13건**이 새로 나왔다(🔴 3 / 🟡 5 / 🟢 5). 전체 목록과 재현 방법은
[`SECURITY_AUDIT_2026-10-15.md`](./SECURITY_AUDIT_2026-10-15.md)에 있다.

이번에 고친 것은 **심각도 '높음' 3건과 하드코딩된 데모 비밀번호**다.
나머지 10건은 **아직 열려 있다**(아래 "남은 항목" 참고).

| # | 심각도 | 문제 | 패치 |
| --- | --- | --- | --- |
| A | 🔴 높음 | **오픈 리다이렉트.** `/login`이 `next` 파라미터를 검증 없이 `redirect()`에 넘겨, `?next=https://evil.example/phish` 로 **정상 로그인 직후 외부 피싱 사이트로** 보낼 수 있었다 | `_safe_next()` 추가 — `/`로 시작하는 내부 경로만 허용하고 `//`·`/\`(브라우저가 `//`로 정규화)는 거부 |
| B | 🔴 높음 | **예약 IDOR.** `login_required`가 "로그인했는가"만 보고 "누구 명의인가"는 검사하지 않아, 폼의 `user_id`만 바꾸면 **타인 명의로 예약**이 생성됐다 | 예약 명의를 `session["user_id"]`에서 가져오도록 변경. 폼 값은 무시하고, **관리자만** 대리 예약으로 타인 지정 가능 |
| C | 🔴 높음 | **빈 비밀번호 계정.** `password`를 빈 문자열로 보내도 그대로 해싱·저장되고 `bcrypt.checkpw(b"", hash)`가 참이 되어 **빈 비밀번호로 로그인**됐다. `role:"admin"`을 함께 보내면 비밀번호 없는 관리자 계정이 됐다 | `_validate_new_user()` 추가 — email 형식·name·비밀번호 10자 이상/앞뒤 공백 금지 검증 후 400 반환 |
| D | 🟡 중간 | 시드 비밀번호가 소스와 README에 하드코딩되어 있었다 — 공개 저장소에 실리면 그대로 크리덴셜 사전에 수집된다 | `SEED_PASSWORD` 환경변수로 분리, 미설정 시 `secrets.token_urlsafe(16)`로 매 실행 무작위 생성 |

**검증**: 세 건 모두 1차 감사와 **동일한 스크립트를 다시 돌려** 결과가 뒤집히는 것을 확인했다.

| 항목 | 패치 전 | 패치 후 |
| --- | --- | --- |
| A — `?next=https://evil.example.com/phish` | `302 Location: https://evil.example.com/phish` | `302 Location: /` |
| B — 홍길동이 관리자 `user_id`로 예약 | 기록된 `user_id` = **관리자** | 기록된 `user_id` = **홍길동 본인** |
| C — 빈 비밀번호 계정 생성 → 로그인 | `201 Created` → 로그인 **성공** | `400 Bad Request` → 계정 자체가 생성 안 됨 |

**회귀 확인**(기능이 깨지지 않았는지): 관리자 대리 예약 정상 동작 ✓ / 일반 사용자가
`user_id` 없이 본인 예약 생성 ✓ / 유효한 입력의 계정 생성 `201` ✓ / 9자 비밀번호 거부 `400` ✓.
예약 폼 템플릿도 함께 수정해, 일반 사용자에게는 예약자 선택 드롭다운 대신 **본인 이름이
고정 표시**된다(서버가 무시하는 입력란을 UI에 남겨두지 않기 위함).

### 남은 항목 — 이번에 고치지 않은 10건

**이 프로젝트는 "보안 점검 완료" 상태가 아니다.** 아래는 확인했지만 아직 열려 있다.

| 심각도 | 항목 |
| --- | --- |
| 🟡 중간 | CSRF 토큰 부재(현재는 브라우저 기본 SameSite=Lax에만 의존) · 이메일 유니크 인덱스 없음(중복 계정 생성 재현됨) · `/health`가 비인증 공개 + 예외에 `str(e)` 노출 · 세션 쿠키 `SECURE=False` · 로그인 시도 제한 없음 + 타이밍으로 계정 열거 가능(존재 165ms vs 미존재 0.6ms) |
| 🟢 낮음 | 이중 예약 허용 · `/logout`이 GET · 스크립트가 비밀번호를 CLI 인자로 전달(`ps` 노출) · 보안 헤더 미설정 · 시드가 확인 없이 전체 삭제 |

## 실행 순서 (부트스트랩)
0. `cluster.env` 를 실제 값으로 채운다 (양쪽 PC의 `tailscale ip -4`, 비밀번호).
1. **PC1**: `bash scripts/00_generate_keyfile.sh` → keyfile 생성 후 PC2로 안전 복사.
2. **PC1/PC2**: `bash scripts/02_firewall.sh` (양쪽 실행).
3. **PC2**: `/tmp/keyfile` 배치 후 `bash scripts/01_setup_pc2.sh` (follower+arbiter 기동).
4. **PC1**: mongod 도 keyFile/replSet 설정으로 기동 (config/mongod-pc1.conf 적용).
5. **PC1**: `03_init_replicaset.js` 실행 → Replica Set 초기화.
6. **PC1**: `04_create_users.js` 실행 → admin/app 계정 생성.
7. **PC1**: `python3 seed/seed_data.py` (MONGO_URI 지정) → 사용자5·회의실10 입력. (요구사항3)
8. **검증**: `06_replication_test.sh` (요구사항4), `05_failover_test.sh` (요구사항5).

## 검증 결과 (2026-09-18, Docker 3노드 실기 검증)

물리 PC 2대가 없어도 로직 자체는 실기로 검증할 수 있습니다. `pc1`/`pc2`/`pc2-arbiter`
세 mongod 컨테이너 + Flask 컨테이너를 Docker 네트워크로 묶어, `cluster.env`의
Tailscale IP 자리만 컨테이너 hostname으로 바꾸고 나머지 로직(리플리카셋 구성·
keyFile·계정 분리·failover 우선순위)은 그대로 실행했습니다.

| 항목 | 실행 내용 | 결과 |
| --- | --- | --- |
| keyFile 생성 | `openssl rand -base64 756`, chmod 400, mongodb 소유 | 3개 컨테이너 공유 볼륨으로 배치 성공 |
| Replica Set 초기화 | `03_init_replicaset.js` 그대로 (pc1 priority2 / pc2 priority1 / arbiter) | pc1이 PRIMARY로 선출 (설계대로 priority 높은 쪽이 우선) |
| 계정 생성 | `04_create_users.js` 그대로 (localhost 예외로 admin 먼저, 이어서 meeting_app readWrite) | 두 계정 모두 생성 성공, 이후 모든 접속에 인증 요구 확인 |
| 시드 데이터 | `seed_data.py` — **dry-run 아님, 실제 MONGO_URI로 실행** | `users 5건, rooms 10건 입력 완료` (실제 DB 카운트로 확인) |
| 복제 테스트 (요구사항4) | pc1(Primary)에 INSERT → pc2(Secondary, `secondaryPreferred`)에서 READ | `[OK] replicated` — 동일 문서 확인 |
| Failover 테스트 (요구사항5) | pc1 강제 종료 → 모니터링 → 새 Primary 쓰기 → pc1 재시작 | pc2가 **약 10초** 만에 PRIMARY로 승격, 승격 직후 쓰기 성공, pc1은 재시작 후 SECONDARY로 정상 재합류 |
| Flask 앱 CRUD (요구사항6) | 실제 리플리카셋에 연결한 Flask 컨테이너에 `/api/users`, `/api/rooms`, `/reservations/new`, `/users`, `/rooms`, `/reservations` 실호출 | 사용자·회의실 생성, 예약 생성 후 목록 페이지에 반영까지 end-to-end 확인. `/health`가 `is_primary` 정확히 보고 |
| Elasticsearch 검색 + 폴백 | ES에 rooms 색인 후 `/rooms?q=` 검색 → ES 컨테이너 종료 → 동일 쿼리 재실행 | ES 가용 시/불가 시 **둘 다** 정상 결과 반환 (Mongo 정규식 폴백 정상 동작 확인) |

**부수 발견**: `requirements.txt`의 `elasticsearch>=8.0`은 상한이 없어, 오늘 `pip install`은
9.x 클라이언트를 받아왔습니다. 이 클라이언트가 8.x 서버에 보내는 `Accept` 헤더 버전이
서버와 맞지 않아 즉시 `BadRequestError`가 납니다. 버전 상한(`elasticsearch>=8.0,<9`)을
명시하지 않으면 오늘 신규 설치 환경에서 이 프로젝트는 ES 연동이 바로 깨집니다.

### 미검증 (실제 Tailscale 멀티호스트 필요)
Docker 컨테이너는 한 호스트의 커널/네트워크 네임스페이스를 공유하므로, 아래는 이번
검증으로 확인할 수 없습니다 — 로직이 아니라 **네트워크 경계** 자체를 실제 두 PC로만
검증할 수 있는 항목입니다.
- Tailscale WireGuard 전송 암호화
- `bindIp`를 실제 Tailscale IP로 제한하는 것 (컨테이너는 `bind_ip_all`로 띄움)
- `ufw`의 `tailscale0` 인터페이스 한정 인바운드 규칙
- Tailscale ACL(`tailscale_acl.json`)의 `tag:meetingdb` 태그 기반 접근 제한

## 완료된 항목 (과거 "다음 단계"였던 것)
Flask 웹앱(`app/`), Doxygen 코드 설명서(`../4_code_doc_doxygen_.../`), SDD/STR 문서
(`../2_...SDD...hwp`, `../3_...STR...hwp`)는 이미 이 폴더 트리에 존재하며 위 표에서
Flask 앱까지 실행 검증을 마쳤습니다. 남은 진짜 다음 단계는 위 "미검증" 항목뿐입니다 —
실제 물리 PC 2대 + Tailscale 환경에서 한 번 더 돌려 이 표를 채우는 것.
