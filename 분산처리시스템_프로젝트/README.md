# 분산 DB 회의실 예약 시스템

MongoDB Replica Set(2 데이터 노드 + Arbiter) 위에 Flask 웹앱을 올린 회의실 예약
시스템입니다. 물리 PC 2대를 Tailscale(WireGuard) 사설망으로 묶어 대학원 "분산처리
시스템" 과목 과제(과제3)로 설계·구현했습니다. 이 폴더에는 같은 과목의 선행
과제(과제1: MongoDB·Elasticsearch 이미지 검색, 과제2: 분산 스토리지/OLAP 발표자료)도
함께 들어 있습니다 — 아래 아키텍처·보안·검증 내용은 메인 프로젝트인 회의실 예약
시스템(과제3) 기준이며, 과제1은 별도 절에서 다룹니다.

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

## 2차 보안 감사 (2026-10-16)

1차 패치(2026-09-18) 이후 **같은 코드를 다시 감사**해 13건을 추가로 찾았고,
그중 심각도 '높음' 3건과 하드코딩된 데모 비밀번호를 패치했습니다.

| 고친 것 | 내용 |
| --- | --- |
| 오픈 리다이렉트 | `/login?next=` 를 검증 없이 `redirect()`에 넘겨 **정상 로그인 직후 외부 피싱 사이트로** 보낼 수 있었음 → 내부 경로만 허용 |
| 예약 IDOR | 폼의 `user_id`만 바꾸면 **타인 명의로 예약** 가능했음 → 세션에서 명의를 가져오고 대리 예약은 관리자만 |
| 빈 비밀번호 계정 | 빈 문자열도 해싱·저장되어 **빈 비밀번호로 로그인**됐음(admin도 가능) → 입력 검증 후 400 |
| 데모 비밀번호 | 시드 비밀번호가 소스·문서에 하드코딩 → `SEED_PASSWORD` 환경변수 / 미설정 시 무작위 생성 |

세 건 모두 **1차와 동일한 스크립트를 다시 돌려** 결과가 뒤집히는 것을 확인했습니다.

**남은 10건(🟡 5 / 🟢 5)은 아직 열려 있습니다** — CSRF 부재, 이메일 중복 허용,
`/health` 예외 노출, 세션 쿠키 플래그, 로그인 시도 제한 없음 등.
전체 목록·재현 방법·패치 상세는
[`박찬종_보완/1_SW_박찬종/README.md`](./박찬종_보완/1_SW_박찬종/README.md)의 "2차 보안 감사" 절을 참고하세요.
**이 프로젝트는 "보안 점검 완료" 상태가 아닙니다.**

## 검증 상태 (2026-09-18)

원본 제출 당시엔 물리 PC 2대 실기에서만 확인 가능했던 리플리카셋 구성·계정 분리·
복제·failover·Flask CRUD·검색 폴백을, Docker 3노드(pc1/pc2/pc2-arbiter) 스택으로
**실제로 돌려 검증**했습니다. failover는 pc1을 강제 종료한 뒤 약 10초 만에 pc2가
Primary로 승격되는 것까지 확인했습니다. 상세 결과와, Docker로는 확인할 수 없는
Tailscale 전송 계층(ACL·방화벽·WireGuard 암호화)의 미검증 목록은
[`박찬종_보완/1_SW_박찬종/README.md`](./박찬종_보완/1_SW_박찬종/README.md)를 참고하세요.

## 과제1 — MongoDB·Elasticsearch 이미지 검색 시스템 (2026.03.22–04.02)

같은 과목의 선행 과제로, COCO 데이터셋에서 person/car 카테고리 이미지를
MongoDB(GridFS)에 적재하고 Elasticsearch 역색인으로 검색하는 파이프라인입니다.

| 스크립트 | 역할 |
| --- | --- |
| `script_1_download_coco.py` | COCO train2017 주석에서 person/car 카테고리 이미지 ID 추출 → `ThreadPoolExecutor(20)` 병렬 다운로드 |
| `script_2_mongodb_setup.py` | GridFS 버킷 `Image_data`에 이미지 바이너리 저장 + `label`/`image_lable` 컬렉션으로 N:M 매핑 |
| `script_3_elasticsearch_setup.py` | 명시적 매핑으로 `image_search_index` 생성 |
| `script_4_sync_and_search.py` | MongoDB → Elasticsearch 벌크 동기화, `labels` term 쿼리 검색 |

실행 결과(제출 보고서 기준): `Image_data` 67,847건 적재, `image_lable` 매핑 76,366건,
`car` 라벨 검색 10건 조회까지 확인.

**코드 확인 결과(수치 불일치)**: 과제 요구사항과 보고서 3-1절은 "10,000장 선별 추출"이라
적었고 스크립트 상단에도 `TARGET_LIMIT = 10000`이 선언돼 있지만, 실제 `fetch_coco_dataset()`은
`target_img_ids = img_ids`로 셔플된 전체 목록을 그대로 반환해 이 상수를 전혀 사용하지
않습니다. 그 결과 person/car 카테고리 전체인 67,847장이 적재됐고(보고서 4-4절 수치와
일치), 이는 실제 실행된 코드와 보고서 서술이 어긋난 지점입니다.

## 폴더 구성

| 폴더 | 내용 |
| --- | --- |
| [`과제1/`](./과제1) | 선행 과제 — COCO 이미지 MongoDB+Elasticsearch 검색 파이프라인(스크립트 4개 + 실습보고서), 위에서 다룬 내용 |
| [`과제2/`](./과제2) | 관련 수업(데이터웨어하우징/OLAP, 분산 스토리지) 발표자료·참고논문 |
| [`과제3/`](./과제3) | 관련 수업(분산DB 회의실 예약 — 같은 주제의 선행 과제) 발표자료·문서 템플릿 |
| [`박찬종_보완/`](./박찬종_보완) | **최종/완성본.** `1_SW_.../`에 인프라 스크립트+Flask 앱, SDD/STR 문서, Doxygen 코드 설명서 포함 — 이번 검증 대상 |
| [`박찬종_제출본/submission/`](./박찬종_제출본) | 실제 채점 제출본 (원본). 크리덴셜은 전부 `CHANGE_ME_...` 플레이스홀더 상태로 남아 있음 |

## 참고

- `cluster.env`, `app/.env.example`에 있던 값은 과제용으로만 쓰인 뒤 이미 폐기된
  값이었지만, 포트폴리오 공개 기준으로 플레이스홀더로 치환했습니다.
- 실행 방법·요구사항 매핑(1~6번)은 `박찬종_보완/1_SW_박찬종/README.md`의
  "실행 순서" 절을 참고하세요.
