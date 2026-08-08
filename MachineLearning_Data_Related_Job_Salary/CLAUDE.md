# CLAUDE.md

이 파일은 이 저장소에서 데이터 분석/모델링 작업을 할 때 Claude Code가 따라야 할 규칙을 정의합니다.
아래 조건들은 `MachineLearning_Team5.ipynb`, `MachineLearning_Team5-2.ipynb`, `MachineLearning_Team5_DataScientistSalary.ipynb` 세 노트북에서 실제로 사용된 분석 관행을 근거로 정리했습니다.

## 데이터셋

- 파일: `ds_salaries.csv`
- 컬럼: `Unnamed: 0`(단순 인덱스, 분석에서 제외), `work_year`, `experience_level`(EN/MI/SE/EX), `employment_type`, `job_title`, `salary`, `salary_currency`, `salary_in_usd`(분석 핵심 종속변수), `employee_residence`, `remote_ratio`, `company_location`, `company_size`(S/M/L)
- 핵심 종속변수는 항상 `salary_in_usd`. `salary`, `salary_currency`는 통화 환산 이전 값이므로 모델 입력에서 제외한다 (`salary_currency`를 피처로 넣으면 사실상 salary_in_usd를 역산할 수 있는 leakage가 됨 — 세 번째 노트북에서 salary_currency_USD/GBP/EUR이 최상위 중요 변수로 나온 것은 이 leakage 때문일 가능성이 높으니 새 분석에서는 기본적으로 제외하고, 포함할 경우 그 이유를 명시할 것).

## 전처리 파이프라인 (합의된 순서)

1. **이상치 제거**: `salary_in_usd` 기준 IQR 방법 사용 (`Q1 - 1.5*IQR` ~ `Q3 + 1.5*IQR`). 임의의 절대값 컷(예: 600,000 초과 제거)은 지양하고 IQR 방식으로 통일한다.
2. **정규성 변환**: log 변환과 Box-Cox 변환을 모두 계산한 뒤 Shapiro-Wilk 검정(p-value)으로 더 정규분포에 가까운 쪽을 선택한다. 표본이 크면 500개를 `random_state=1`로 샘플링해서 검정한다.
3. **직무 그룹 단순화(선택적)**: `job_title`은 카디널리티가 매우 높으므로 필요 시 `scientist/engineer/analyst/manager/architect/developer/other`로 묶는 `simplify_job_title()` 류의 함수를 사용할 수 있다. 다만 XGBoost 기반 노트북에서는 원본 `job_title`을 그대로 원-핫 인코딩해서 더 세밀한 변수 중요도를 얻었으므로, 트리 기반 모델에서는 원본을 우선 사용하고 로지스틱/선형 회귀처럼 차원에 민감한 모델에서만 단순화를 고려한다.
4. **타겟 라벨링**: 회귀가 아닌 분류 문제로 프레이밍할 때는 정규성 개선된 값(log 또는 Box-Cox 변환값) 기준 33/66 분위수로 `Low/Medium/High` 3-class 라벨을 만드는 것이 기본값이다. 평균 기준 이진 분류(High/Low)는 시도됐지만 정보 손실이 크므로 기본으로 쓰지 않는다. GMM(Gaussian Mixture Model) 기반 라벨링도 대안으로 실험되었으니 분포가 다봉형(multimodal)으로 보이면 고려할 수 있다.
5. **범주형 인코딩**: `pd.get_dummies`로 원-핫 인코딩. 회귀 계열 모델은 다중공선성(더미 변수 트랩) 방지를 위해 `drop_first=True`를 사용하고, 트리 계열(XGBoost/RandomForest)은 `drop_first=False`도 허용되지만 되도록 `drop_first=True`로 통일해 컬럼 수를 줄인다.
6. **결측치**: 매 분석 시작 시 `isnull().sum()`으로 확인 후 진행. 이 데이터셋은 결측치가 없는 것이 확인되어 있으므로, 결측치가 나타나면 데이터 소스가 바뀐 것이니 먼저 원인을 확인한다.

## 모델링 규칙

- **`random_state=42`를 모든 `train_test_split`, 모델 초기화(RandomForest, XGBoost 등)에 일관되게 사용**한다. 재현성 비교가 이 프로젝트의 핵심이므로 값을 바꾸지 않는다.
- **`test_size=0.2`**를 기본 train/test 분할 비율로 사용한다.
- **다중공선성 체크**: 회귀모델을 쓸 때는 VIF(Variance Inflation Factor)를 계산해서 확인한다. 원-핫 인코딩된 카테고리를 상수항과 함께 전부 넣으면 VIF가 무한대가 되는 더미 변수 트랩이 발생하므로 주의(반드시 `drop_first=True` 또는 상수항 제외).
- **PCA는 이 데이터셋에서 비효율적**임이 이미 확인됨 (95% 분산 설명에 105개 성분 필요, 차원 축소 효과 미미, R²가 오히려 -10 수준으로 악화). 차원 축소가 필요하면 PCA 대신 **XGBoost `feature_importances_` 누적 95% 기준 변수 선택**을 우선 사용한다.
- **분류 모델 비교 기준선**: Random Forest(RandomizedSearchCV로 `n_estimators`, `max_depth`, `min_samples_split`, `min_samples_leaf`, `max_features` 튜닝)와 XGBoost(`multi:softprob`, `num_class=3`)를 기본 비교 대상으로 삼는다. 두 모델 모두 정확도 약 0.65~0.68 수준이 이 데이터셋에서의 현실적인 성능 상한선에 가깝다는 것이 확인되어 있으므로, 이보다 훨씬 높은 정확도가 나오면 데이터 누수(leakage)를 의심할 것 (특히 `salary_currency`, `salary` 원본 포함 여부 확인).
- **클래스 불균형 처리(SMOTE + class_weight='balanced')는 이 데이터셋에서 오히려 성능을 저하시켰다**(정확도 및 F1 하락, 특히 Medium 클래스 recall 개선 실패). 따라서 클래스 불균형 보정 기법을 기본으로 적용하지 않으며, 적용하려면 반드시 적용 전/후 성능을 비교해서 개선이 확인될 때만 채택한다.
- **`Medium` 클래스는 구조적으로 가장 분류가 어려운 클래스**로 세 노트북에서 일관되게 확인됨 (Low/High 대비 precision·recall이 낮음). 새로운 모델의 성능을 평가할 때 전체 accuracy뿐 아니라 Medium 클래스의 precision/recall을 별도로 보고할 것.

## 평가 및 보고 형식

- 회귀: MSE, RMSE, R² 세 지표를 항상 함께 보고한다.
- 분류: `accuracy_score` + `classification_report`(클래스별 precision/recall/f1) + `confusion_matrix` 시각화(heatmap)를 기본 세트로 사용한다.
- 시각화는 `matplotlib`/`seaborn` 사용, 결과 해석은 마크다운 셀에 한국어로 정리하는 기존 스타일을 따른다.
- 새 모델/전처리 방법을 시도할 때는 반드시 기존 노트북에서 나온 baseline 수치(Linear Regression R²≈0.43, RandomForest/XGBoost accuracy≈0.65~0.68)와 비교해서 개선 여부를 명시한다.

## 하지 말아야 할 것

- `salary_currency`, `salary`(원본, 비-USD)를 피처로 사용해 타겟 누수를 일으키지 말 것.
- PCA를 기본 차원 축소 수단으로 재시도하지 말 것 (이미 비효율적임이 검증됨).
- SMOTE/class_weight 균형화를 검증 없이 기본 적용하지 말 것.
- `random_state`를 42가 아닌 다른 값으로 바꿔서 이전 결과와 비교 불가능하게 만들지 말 것.
