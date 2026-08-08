# 데이터 관련 직무 연봉 분석 및 예측 (Data-Related Job Salary Analysis)

`ds_salaries.csv` 데이터를 이용해 데이터 관련 직무(Data Scientist, ML Engineer 등)의 연봉을 **설명(EDA/통계)** 하고 **예측(분류 모델)** 하는 프로젝트입니다.

## 문제 정의

- 데이터: 약 600행, `job_title`(50+ 종), `employee_residence`/`company_location`(각 70여개국) 등 행 수 대비 카디널리티가 매우 높은 범주형 변수가 많은 작은 정형 데이터셋
- 타겟: `salary_in_usd` (연봉을 log/Box-Cox 변환 후 33/66 분위수로 `Low/Medium/High` 3-class 분류 문제로 프레이밍)
- 핵심 이슈: `salary`, `salary_currency`는 `salary_in_usd`의 파생 변수이므로 피처에 포함하면 타겟 누수(leakage) 발생 — 실제로 이 두 컬럼을 포함했을 때 정확도가 비정상적으로 높게 나오는 현상을 확인하고 원인을 규명함

## 접근 방법

1. IQR 기반 이상치 제거
2. log/Box-Cox 변환 중 Shapiro-Wilk 검정으로 더 정규분포에 가까운 변환 선택
3. `pd.get_dummies(drop_first=True)` 원-핫 인코딩 (다중공선성 방지, VIF로 검증)
4. Random Forest / XGBoost 비교, `RandomizedSearchCV` 하이퍼파라미터 튜닝
5. PCA는 시도했으나 비효율적임을 확인(105개 성분 필요, 성능 개선 없음) → XGBoost `feature_importances_` 기반 변수 선택으로 대체
6. SMOTE + `class_weight='balanced'` 클래스 불균형 보정을 시도했으나 오히려 성능 저하 확인 → 기본 적용하지 않기로 결정

## 결과

- 3-class(Low/Medium/High) 분류 정확도 **약 67.5%** (Random Forest/XGBoost 공통 상한선 0.65~0.68 수준)
- High/Low는 F1 0.72~0.73 수준으로 비교적 안정적, **Medium 클래스는 구조적으로 가장 분류가 어려운 클래스**로 세 실험 노트북에서 일관되게 확인 (F1 0.57~0.60)
- Linear Regression 기준 R² ≈ 0.43

## 파일 구성

- `ds_salaries.csv` — 원본 데이터
- `MachineLearning_Team5.ipynb`, `MachineLearning_Team5-2.ipynb`, `MachineLearning_Team5_DataScientistSalary.ipynb` — 실험 버전별 분석 노트북
- `CLAUDE.md` — 위 세 노트북에서 실제로 검증된 분석 규칙/합의 사항 정리
- `CLAUDE_PROPOSED.md` — 처음부터 이 프로젝트를 설계한다면 따를 방법론 제안본 (설명적 분석과 예측적 모델링을 명확히 분리하는 접근)

## 배운 점

- 파생 변수를 피처로 넣었을 때의 데이터 누수를 정량적으로 탐지하고 원인을 규명한 경험
- PCA, SMOTE처럼 "일반적으로 도움이 될 것 같은" 기법이 특정 데이터셋에서는 오히려 성능을 해칠 수 있음을 실험으로 확인하고, 근거 없이 채택하지 않는 판단 기준을 세움
