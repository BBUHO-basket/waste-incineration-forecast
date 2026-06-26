"""
자원회수시설 쓰레기 반입량 예측 XGBoost 모델 학습 스크립트
실행: python train_incoming_model.py
"""
import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'features', '자원회수시설_프로젝트용_전처리_월평균추가.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'incoming_xgb_model.pkl')

FEATURES = [
    'prev_month_incoming_ton',
    'prev_2month_avg_incoming_ton',
    'prev_3month_avg_incoming_ton',
    'same_month_last_year_incoming_ton',
]
TARGET = 'incoming_ton'

def train():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')
    df = df.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)
    print(f'학습 데이터: {len(df)}행  |  시설: {list(df["facility"].unique())}')

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)

    print(f'\n── 테스트셋 성능 ──')
    print(f'MAE  : {mae:,.1f} ton')
    print(f'RMSE : {rmse:,.1f} ton')
    print(f'R²   : {r2:.4f}')

    # 피처 중요도
    print('\n── 피처 중요도 ──')
    for feat, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
        print(f'  {feat:<45}: {imp:.4f}')

    joblib.dump(model, MODEL_PATH)
    print(f'\n모델 저장 완료: {MODEL_PATH}')

if __name__ == '__main__':
    train()
