"""
소각비율 예측 XGBoost 모델 학습
입력: same_month_past_avg_incineration_rate
출력: incineration_rate
실행: python train_incineration_model.py
"""
import pandas as pd
import numpy as np
import joblib, os
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'features', '자원회수시설_프로젝트용_전처리_월평균추가.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'incineration_xgb_model.pkl')

FEATURE = 'same_month_past_avg_incineration_rate'
TARGET  = 'incineration_rate'

def train():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')
    df = df.dropna(subset=[FEATURE, TARGET])
    df = df[np.isfinite(df[TARGET]) & (df[TARGET] <= 2.0) & (df[TARGET] > 0)]
    df = df.reset_index(drop=True)
    print(f'학습 데이터: {len(df)}행')

    X = df[[FEATURE]]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=3,
        subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f'MAE : {mean_absolute_error(y_test, y_pred):.4f}')
    print(f'RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}')
    print(f'R²  : {r2_score(y_test, y_pred):.4f}')

    joblib.dump(model, MODEL_PATH)
    print(f'모델 저장 완료: {MODEL_PATH}')

if __name__ == '__main__':
    train()
