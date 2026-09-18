# Python Data Analysis / ML Portfolio

데이터 분석 및 머신러닝 프로젝트 모음입니다. 각 프로젝트는 팀/개인 과제로 진행했으며, 폴더별 README에 문제 정의·접근 방법·결과를 정리했습니다.

## 프로젝트 목록

| 프로젝트 | 주제 | 핵심 내용 |
|---|---|---|
| [MachineLearning_Data_Related_Job_Salary](./MachineLearning_Data_Related_Job_Salary) | 데이터 직무 연봉 분석/예측 | **과거 분석 재검증 후 회귀로 재구축.** 리키지로 알던 변수가 실제로는 중복 변수였음을 규명. Ridge+log1p, 교차검증 R² 0.500±0.069 (MAPE 42.6%) |
| [데사프_프로젝트](./데사프_프로젝트) | 뇌졸중 발병 예측 (팀 과제) | **과거 분석 재검증 후 불균형 관점으로 재구축.** "정확도 95%"가 환자 0명 검출 모델의 수치임을 확인. PR-AUC 0.225±0.043 (무작위 기준선 0.049), 재현율 0.787 |
| [인공지능 프로젝트](./인공지능%20프로젝트) | 사진 → 감정 → 이모지 매칭 | **7개 감정 분류 CNN 재학습 완료.** `validation_split`이 `train/`·`test/` 양쪽에 걸려 약 5,700장씩 버려지던 버그를 고쳐 재학습(Run B) → 동일한 전체 test(7,178장) 기준 **0.5954**, 버그 그대로 재현한 Run A(0.5720)보다 **+4.1%**. 3년 만의 **혼동행렬**로 확인: 가장 표본이 적은 `disgusted`(111장)가 가장 낮은 성능(F1 0.351) — 표본 부족이 실제 손해로 이어짐을 수치로 확정. 3년간 막혀 있던 **이모지 할당 단계도 완성** — CNN을 이모지에 돌릴 필요 없이 `emoji_df.csv`의 `name` 칸에 레이블이 이미 있었음(대응표 54/105) |
| [회귀분석_조별과제](./회귀분석_조별과제) | 와인 품질 회귀분석 (팀 과제) | **두 개 트랙을 모두 재검증 — 주장·절차 13건 중 12건이 성립하지 않음.** 1부(적포도주 OLS): 최대 영향 변수로 지목한 `density`는 표준화 시 10위·p=0.409 비유의(단위 착시), 핵심 이슈로 든 고상관은 백포도주 값, R²=1.0은 `quality`가 특성에 포함된 타깃 누수, 중복 240행이 RandomForest만 0.129 부풀림. OLS 5-fold CV R² 0.342±0.064. 2부(백+적 병합 ML, `회귀분석최종코드.ipynb`): 자랑하던 **RandomForest R² 0.712는 업샘플링을 분할 전에 수행한 누수** — 테스트의 59.6%가 훈련에 쌍둥이 보유, 순서만 바로잡으면 **0.548**. 변환 비교 40여 셀은 변환 함수가 타겟 `quality`까지 변환해 **비교 자체가 불가**(타겟 고정 시 효과 소멸) |
| [분산처리시스템_프로젝트](./분산처리시스템_프로젝트) | MongoDB Replica Set 회의실 예약 시스템 (개인 과제) | 물리 PC 2대 실기에서만 검증 가능했던 리플리카셋·failover·Flask CRUD를 **Docker 3노드로 실제 재현·검증**. pc1 강제 종료 후 **약 10초 만에 pc2가 Primary로 승격**, 재시작 후 정상 재합류까지 확인. 부수 발견: `requirements.txt`의 `elasticsearch>=8.0` 상한 미지정으로 오늘 설치 시 9.x 클라이언트가 8.x 서버와 충돌. Tailscale 전송 계층(ACL·방화벽·WireGuard)은 Docker로 검증 불가 — 별도 명시 |
| [photo2emoji-service](./photo2emoji-service) | 사진→감정→이모지 **서빙 API** | **노트북에서만 돌던 파이프라인을 FastAPI 서비스로 제품화.** 재학습된 CNN(Run B) + 이모지 매칭 규칙을 `POST /predict`로 서빙, 웹 데모 페이지 포함. **pytest 10개 통과**(응답 구조·확률 합·4xx 입력 처리·매칭 규칙 단위 테스트), venv·**Docker 컨테이너 양쪽에서 실측 응답 확인**(happy 0.9973→😁, surprised 0.8633→😲). 한계 명시: 품질 상한 = 1단계 CNN 정확도 0.5954, 얼굴 검출 단계 없음 `[미검증]` |

## 사용 기술

- Python, pandas, numpy
- scikit-learn (Random Forest, XGBoost, Logistic/Linear Regression, SMOTE)
- statsmodels (OLS, VIF)
- matplotlib, seaborn
- Jupyter Notebook

## 참고

- 각 노트북은 수업/스터디 팀 과제로 작성되었으며, 팀 과제의 경우 본인이 담당한 분석 파트를 중심으로 포함되어 있습니다.
- `MachineLearning_Data_Related_Job_Salary`에는 실제 분석에서 검증된 규칙을 정리한 `CLAUDE.md`가 포함되어 있어, 분석 과정에서의 의사결정 근거를 확인할 수 있습니다.
