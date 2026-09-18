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
