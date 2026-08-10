# CLAUDE.md

이 파일은 이 저장소에서 데이터 분석/모델링 작업을 할 때 Claude Code가 따라야 할 규칙을 정의합니다.
**`MachineLearning_Team5.ipynb`(60셀, 로컬 base 커널에서 실제 실행 완료)를 기준(source of truth)** 으로 정리했습니다.
`MachineLearning_Team5-2.ipynb`, `MachineLearning_Team5_DataScientistSalary.ipynb`는 실험 과정에서 나온 별도 버전이며, 이 문서와 어긋나는 부분이 있으면 `MachineLearning_Team5.ipynb`의 실제 실행 결과를 우선한다.

## 데이터셋

- 파일: `ds_salaries.csv` (607행, 12컬럼)
- 컬럼: `Unnamed: 0`(단순 인덱스, 제외), `work_year`, `experience_level`(EN/MI/SE/EX), `employment_type`, `job_title`(**49종**), `salary`, `salary_currency`, `salary_in_usd`(핵심 종속변수), `employee_residence`, `remote_ratio`, `company_location`, `company_size`(S/M/L)
- 결측치 없음 (`MachineLearning_Team5.ipynb` 셀 8에서 실행 확인)
- **⚠️ `salary_currency` 리키지 미해결**: `salary`, `salary_currency`는 `salary_in_usd`의 파생 값이라 타겟 누수(leakage) 위험이 있다는 점은 이전부터 인지되어 있었지만, **`MachineLearning_Team5.ipynb`의 실제 회귀(셀 8, 12)·분류(셀 35, 38) 코드 모두 `salary_currency`를 categorical feature로 그대로 포함**하고 있다. 실제로 XGBoost 변수 중요도(셀 35)에서 `salary_currency_GBP`가 2위(중요도 0.0898), `salary_currency_USD`가 5위(0.0387)로 확인됨 — 즉 아래에 기록된 정확도(RF 0.5917, XGBoost 0.6833)는 **리키지가 포함된 상태의 수치**다. `salary`는 세 컬럼 제외 목록(`'salary','salary_in_usd','salary_class'`)에 포함되어 정상적으로 제외되어 있다.

## 전처리 파이프라인 (실제 실행된 순서)

1. **이상치 제거**: `salary_in_usd` 기준 IQR 방법. 607행 → 597행으로 10건 제거됨.
2. **정규성 변환**: log 변환과 Box-Cox 변환을 모두 계산해 비교. Box-Cox 변환 후 요약통계 `mean≈2124.3`, `std≈786.8` 확인됨 (셀 6).
3. **⚠️ 라벨 컬럼이 2개 존재함 — 주의 필요**:
   - `salary_class`: **원본(정제 전) `salary_in_usd`** 기준 33/66 분위수(경계값 `76,940` / `130,000`)로 만든 Low/Medium/High 라벨. 분포는 High 206 / Low 201 / Medium 200 (전체 607행 기준, 셀 4).
   - `salary_class_`: IQR 제거 후 **Box-Cox 변환값** 기준 33/66 분위수로 만든 라벨. 분포는 Medium 202 / Low 199 / High 196 (`df_clean` 597행 기준, 셀 6).
   - 실제 분류 모델링 셀(RandomForest 셀 38, XGBoost 셀 47 등)은 **`salary_class`를 타겟(y)으로 사용**한다 — 즉 Box-Cox로 정규성을 개선한 `salary_class_`가 아니라 원본 분위수 기준 라벨을 쓰고 있음. 새로 분석할 때 이 둘을 혼동하지 말고, 어느 라벨을 쓰는지 명시할 것.
4. **직무 그룹 단순화(선택적, 검증 결과: 권장하지 않음)**: `job_title`(49종, 원-핫 시 변수 190개 내외)을 `scientist/engineer/analyst/manager/architect/developer/other` 7그룹(`job_group`)으로 단순화하는 `simplify_job_title()` 함수가 있다 (셀 56, 58). **실행 결과 Logistic Regression 기준 정확도 0.5667**로, 원본 `job_title` 기반 Random Forest(0.5917)·XGBoost(0.6833)보다 낮고 변수 개수도 138개로 크게 줄지 않아 **채택하지 않는다**. XGBoost 계열은 `feature_importances_` 누적 95% 기준 변수 선택(36개 변수로 축소, 셀 35)을 그대로 사용한다.
5. **범주형 인코딩**: `pd.get_dummies` 사용.
   - **⚠️ 회귀 섹션(Linear Regression, 셀 8·12·16)은 `drop_first=False`로 인코딩**했고, 그 결과 VIF 진단(셀 22)에서 `employee_residence_MD` VIF≈5.5×10⁶ 등 극단적 다중공선성(더미 변수 트랩)이 확인됐다. 이는 의도된 실험이 아니라 확인된 버그성 이슈이므로, **회귀 계열 모델은 반드시 `drop_first=True`로 다시 인코딩**해야 한다.
   - 분류 섹션(RandomForest/XGBoost, 셀 35 이후)은 `drop_first=True`를 사용해 이 문제가 없다.
6. **GMM(Gaussian Mixture Model)** 기반 라벨링도 실험됨(셀 32-33, Box-Cox 변환값에 대해 클러스터링). 분포가 다봉형으로 보일 때 대안으로 고려 가능하나, 최종 모델링에는 채택되지 않았다.

## 모델링 규칙 및 실측 결과

- `random_state=42`, `test_size=0.2`를 모든 `train_test_split`/모델 초기화에 일관 사용.
- **Linear Regression** (drop_first=False, 다중공선성 있는 상태): MSE≈1.513×10⁹, **RMSE≈38,899**, **R²≈0.4319**. 표준화(StandardScaler) 후에도 R²≈0.4347로 개선 미미.
- **PCA는 비효율적임이 재확인됨**: 95% 분산 설명에 **105개 성분** 필요, PCA 축소 후 회귀 시 **R²≈-10.4053**(RMSE≈174,297로 폭증) — 오히려 성능 대폭 악화. PCA를 기본 차원 축소 수단으로 쓰지 말 것.
- **Random Forest** (`RandomizedSearchCV`, best params: `n_estimators=150, min_samples_split=5, min_samples_leaf=2, max_features='log2', max_depth=10`): **정확도 0.5917**. (※ 노트북 내 마크다운 해설 셀은 "Accuracy 65%"라고 적혀 있으나 실제 실행 출력은 0.5917이다 — 마크다운 해설이 이전 실행/다른 버전 결과를 그대로 남긴 것으로 보이므로, 신뢰할 값은 실제 실행 출력이다.)
- **SMOTE + `class_weight='balanced'`**: 정확도 **0.5583**으로 기본 RF(0.5917)보다 더 낮음 — 클래스 불균형 보정이 이 데이터셋에서 성능을 저하시킨다는 기존 결론 재확인. 기본 적용하지 않는다.
- **XGBoost** (`multi:softprob`, `num_class=3`, top 36개 변수): **정확도 0.6833**, 이 프로젝트에서 가장 높은 성능.
- **XGBoost + RandomizedSearchCV 튜닝**: CV 기준 `Best CV weighted F1: 0.7032`, best params `subsample=1.0, reg_lambda=1, reg_alpha=0, n_estimators=100, max_depth=3, learning_rate=0.05, gamma=0.1, colsample_bytree=0.6`. **다만 튜닝 후 최종 평가 셀(53)의 출력이 튜닝 전(셀 47)과 정확도가 완전히 동일(0.6833)** — 튜닝된 모델이 실제로 재평가에 반영됐는지 의심되는 지점이므로, 이 부분을 다시 실행/검증할 때는 `model` 변수가 튜닝된 모델(`best_estimator_`)을 가리키는지 먼저 확인할 것.
- **`Medium` 클래스가 구조적으로 가장 분류가 어려움** — RF/XGBoost 모두 Medium이 다른 두 클래스로 새는 경향 일관 확인. 새 모델 평가 시 전체 accuracy와 별도로 Medium precision/recall을 반드시 함께 보고할 것.

## 평가 및 보고 형식

- 회귀: MSE, RMSE, R² 세 지표를 항상 함께 보고.
- 분류: `accuracy_score` + `classification_report` + `confusion_matrix` 시각화를 기본 세트로 사용.
- 새 실험은 아래 **리키지 제거 후 최종 baseline**과 비교해 개선 여부를 명시한다.

### 리키지 제거 후 최종 baseline (`MachineLearning_Team5.ipynb` 마지막 섹션 "사후 검증"에서 실측)

`salary_currency`를 피처에서 제거하고(회귀는 `drop_first=True`로 VIF 버그도 함께 수정) 재실행한 결과:

| 모델 | 리키지 포함(구) | 리키지 제거(신, 채택) |
| --- | --- | --- |
| Linear Regression R² | 0.4319 | **0.4134** |
| Random Forest 정확도 | 0.5917 | **0.6083** |
| XGBoost 정확도(축소 피처 28개) | 0.6833 | **0.6917** |
| XGBoost 정확도(전체 피처, 축소 전) | 미측정 | 0.6750 |

- 분류(RF/XGBoost)는 `salary_currency` 제거 후 **오히려 정확도가 올랐다** — 즉 이 컬럼은 3-class 분류에서 신호보다 노이즈/과적합 요인에 가까웠다. 회귀는 R²가 소폭 하락해 통화 정보가 절대 연봉값 예측에는 약한 신호로 작용했을 가능성이 있다.
- 전체 피처(0.6750) vs 축소 피처(0.6917) 비교로, 변수중요도 기반 차원 축소가 유의미하다는 기존 결론이 리키지 제거 후에도 유지됨을 확인했다.
- **앞으로 새 실험/비교의 기준값은 이 표의 "리키지 제거" 열이다.** 위 "모델링 규칙 및 실측 결과" 섹션에 남아있는 리키지 포함 수치(RF 0.5917, XGBoost 0.6833)는 참고용 구버전으로만 취급할 것.

## 하지 말아야 할 것

- `salary_currency`를 회귀/분류 피처로 사용해 타겟 누수를 일으키지 말 것. **`MachineLearning_Team5.ipynb`의 초반 회귀/분류 셀들은 이 원칙을 어기고 있었고(리키지 포함 상태로 원래 실행됨), 노트북 마지막 "사후 검증" 섹션에서 이를 발견해 제거 후 재실행한 결과를 별도로 추가했다.** 새 작업은 반드시 이 "사후 검증" 섹션의 리키지 제거 baseline을 기준으로 삼고, 초반 셀들의 리키지 포함 수치를 그대로 인용하지 말 것.
- PCA를 기본 차원 축소 수단으로 재시도하지 말 것 (105개 성분 필요, R²가 오히려 -10 수준으로 악화됨이 실측으로 확인됨).
- SMOTE/class_weight 균형화를 검증 없이 기본 적용하지 말 것 (실측상 정확도 0.5917→0.5583으로 악화).
- `job_group`(job_title 단순화)을 기본으로 채택하지 말 것 (실측 정확도 0.5667로 원본 job_title 대비 낮음). 로지스틱 회귀 등에서 차원 축소가 꼭 필요할 때만 참고용으로 재검토.
- `random_state`를 42가 아닌 값으로 바꿔서 이전 결과와 비교 불가능하게 만들지 말 것.
- 회귀 섹션에서 `pd.get_dummies(..., drop_first=False)`를 그대로 두지 말 것 — VIF 폭증(다중공선성) 원인이므로 `drop_first=True`로 고쳐서 재실행할 것.
- `salary_class`(원본 분위수 라벨)와 `salary_class_`(Box-Cox 분위수 라벨)를 혼동하지 말 것 — 어느 라벨을 타겟으로 쓰는지 코드에 명시할 것.
