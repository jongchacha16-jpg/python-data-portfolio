# 분산 DB 회의실 예약 시스템

MongoDB Replica Set(2 데이터 노드 + Arbiter) 위에 Flask 웹앱을 올린 회의실 예약
시스템입니다. 물리 PC 2대를 Tailscale(WireGuard) 사설망으로 묶어 대학원 "분산처리
시스템" 과목 과제로 설계·구현했습니다.

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

데이터 노드가 2개뿐이면 과반수(majority)가 2라 Leader 하나만 죽어도 자동 failover가
안 됩니다. PC2에 데이터를 갖지 않는 **Arbiter**를 하나 추가해 `데이터1+Arbiter1=2=과반`을
만들어, PC1이 죽어도 PC2가 새 Primary로 승격되도록 설계했습니다.

## 보안 계층

1. **네트워크 노출 차단** — mongod `bindIp` = loopback + Tailscale IP만
2. **방화벽(ufw)** — 27017/27018/9200은 `tailscale0` 인터페이스 유입만 허용
3. **Tailscale ACL** — `tag:meetingdb` 두 노드끼리만 해당 포트 통신 허용
4. **멤버 내부 인증** — 동일 `keyFile`로 Replica Set 멤버 인증
5. **클라이언트 인증(SCRAM)** — `admin`(root) / `meeting_app`(readWrite, 최소권한) 분리
6. **전송 암호화** — 모든 노드 간 트래픽이 Tailscale WireGuard 터널로 암호화

## 검증 상태 (2026-09-18)

원본 제출 당시엔 물리 PC 2대 실기에서만 확인 가능했던 리플리카셋 구성·계정 분리·
복제·failover·Flask CRUD·검색 폴백을, Docker 3노드(pc1/pc2/pc2-arbiter) 스택으로
**실제로 돌려 검증**했습니다. failover는 pc1을 강제 종료한 뒤 약 10초 만에 pc2가
Primary로 승격되는 것까지 확인했습니다. 상세 결과와, Docker로는 확인할 수 없는
Tailscale 전송 계층(ACL·방화벽·WireGuard 암호화)의 미검증 목록은
[`12215333_박찬종_보완/1_SW_12215333_박찬종/README.md`](./12215333_박찬종_보완/1_SW_12215333_박찬종/README.md)를 참고하세요.

## 폴더 구성

| 폴더 | 내용 |
| --- | --- |
| [`12215333_박찬종_보완/`](./12215333_박찬종_보완) | **최종/완성본.** `1_SW_.../`에 인프라 스크립트+Flask 앱, SDD/STR 문서, Doxygen 코드 설명서 포함 — 이번 검증 대상 |
| [`12215333_박찬종/submission/`](./12215333_박찬종) | 실제 채점 제출본 (원본). 크리덴셜은 전부 `CHANGE_ME_...` 플레이스홀더 상태로 남아 있음 |
| [`과제2/`](./과제2) | 관련 수업(데이터웨어하우징/OLAP, 분산 스토리지) 발표자료·참고논문 |
| [`과제3/`](./과제3) | 관련 수업(분산DB 회의실 예약 — 같은 주제의 선행 과제) 발표자료·문서 템플릿 |

## 참고

- `cluster.env`, `app/.env.example`에 있던 값은 과제용으로만 쓰인 뒤 이미 폐기된
  값이었지만, 포트폴리오 공개 기준으로 플레이스홀더로 치환했습니다.
- 실행 방법·요구사항 매핑(1~6번)은 `12215333_박찬종_보완/1_SW_12215333_박찬종/README.md`의
  "실행 순서" 절을 참고하세요.
