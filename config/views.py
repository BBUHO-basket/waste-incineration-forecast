from django.shortcuts import render, redirect
import os
import numpy as np
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING_MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'incoming_xgb_model.pkl')
FACILITY_CSV_PATH   = os.path.join(BASE_DIR, 'data', 'features', '자원회수시설_프로젝트용_전처리_월평균추가.csv')
ALLOWANCE_CSV_PATH  = os.path.join(BASE_DIR, 'data', 'raw', '서울특별시_탄소배출량_허용량.csv')

FACILITIES = ['강남', '노원', '마포', '양천']

# 생활폐기물 소각 CO2 배출계수 (2024년 승인 국가 온실가스 배출·흡수계수)
# 종이류, 고무류, 피혁류, 플라스틱류, 섬유류, 기타 단순평균
_DM_VALUES = [0.8391, 0.9614, 0.9215, 0.8855, 0.7763, 0.6770]
_CF_VALUES = [0.4144, 0.6986, 0.6003, 0.7230, 0.5176, 0.4859]
_DM_AVG = sum(_DM_VALUES) / len(_DM_VALUES)
_CF_AVG = sum(_CF_VALUES) / len(_CF_VALUES)
CO2_EMISSION_FACTOR = _DM_AVG * _CF_AVG * (44 / 12)  # tCO2/ton 소각

# 서울시 연간 탄소배출 허용량 (tCO2/year)
_CARBON_ALLOWANCES = None

_incoming_model = None
_facility_df    = None


def _load_incoming_model():
    global _incoming_model
    if _incoming_model is None:
        _incoming_model = joblib.load(INCOMING_MODEL_PATH)
    return _incoming_model


def _load_facility_df():
    global _facility_df
    if _facility_df is None:
        _facility_df = pd.read_csv(FACILITY_CSV_PATH, encoding='utf-8-sig')
    return _facility_df


def _load_carbon_allowances():
    global _CARBON_ALLOWANCES
    if _CARBON_ALLOWANCES is None:
        df = pd.read_csv(ALLOWANCE_CSV_PATH, encoding='utf-8-sig')
        row = df.iloc[0]
        _CARBON_ALLOWANCES = {}
        for col in df.columns:
            try:
                year = int(col)
                val = str(row[col]).replace(',', '')
                _CARBON_ALLOWANCES[year] = float(val)
            except (ValueError, TypeError):
                pass
    return _CARBON_ALLOWANCES


def _normalize_ym(year, month):
    while month <= 0:
        year -= 1
        month += 12
    while month > 12:
        year += 1
        month -= 12
    return year, month


def _get_incoming_real(df, facility, year, month):
    year, month = _normalize_ym(year, month)
    row = df[(df['facility'] == facility) & (df['year'] == year) & (df['month'] == month)]
    if len(row) > 0 and not pd.isna(row.iloc[0]['incoming_ton']):
        return float(row.iloc[0]['incoming_ton'])
    return None


def _get_same_month_past_rates(df, facility, target_year, target_month):
    """target_year 이전 같은 달 실제 소각비율 dict {year: rate}"""
    past = df[
        (df['facility'] == facility) &
        (df['month'] == target_month) &
        (df['year'] < target_year)
    ][['year', 'incineration_rate']].copy()
    past['incineration_rate'] = past['incineration_rate'].replace([np.inf, -np.inf], np.nan)
    past = past.dropna(subset=['incineration_rate'])
    past = past[(past['incineration_rate'] > 0) & (past['incineration_rate'] <= 2.0)]
    return dict(zip(past['year'].tolist(), past['incineration_rate'].tolist()))


def _predict_recursive(facility, target_year, target_month):
    """반입량 재귀 예측. 반환: (예측값, 중간예측 dict)"""
    df = _load_facility_df()
    model = _load_incoming_model()
    cache = {}
    predicted_months = {}

    def get_value(y, m):
        y, m = _normalize_ym(y, m)
        if (y, m) in cache:
            return cache[(y, m)]
        real = _get_incoming_real(df, facility, y, m)
        if real is not None:
            cache[(y, m)] = real
            return real
        return None

    def predict_month(y, m):
        y, m = _normalize_ym(y, m)
        if (y, m) in cache:
            return cache[(y, m)]
        pm1  = get_value(y, m - 1) or predict_month(y, m - 1)
        pm2  = get_value(y, m - 2) or predict_month(y, m - 2)
        pm3  = get_value(y, m - 3) or predict_month(y, m - 3)
        smly = get_value(y - 1, m) or predict_month(y - 1, m)
        X = np.array([[pm1, (pm1 + pm2) / 2, (pm1 + pm2 + pm3) / 3, smly]])
        pred = max(0.0, float(model.predict(X)[0]))
        cache[(y, m)] = pred
        predicted_months[(y, m)] = pred
        return pred

    result = predict_month(target_year, target_month)
    return result, predicted_months


def _estimate_annual_incin_ton(facility, year, df):
    """
    시설의 연간 소각량(ton) 추정.
    실데이터 있으면 실데이터, 없으면 예측 반입량 × 과거동월 평균 소각비율.
    """
    total = 0.0
    for m in range(1, 13):
        row = df[(df['facility'] == facility) & (df['year'] == year) & (df['month'] == m)]
        if len(row) > 0:
            val = row.iloc[0].get('incineration_ton', np.nan)
            if pd.notna(val) and np.isfinite(float(val)) and float(val) > 0:
                total += float(val)
                continue
        # 실데이터 없으면 예측
        pred_incoming, _ = _predict_recursive(facility, year, m)
        past_rates = _get_same_month_past_rates(df, facility, year, m)
        rate = float(np.mean(list(past_rates.values()))) if past_rates else 1.0
        total += pred_incoming * rate
    return total


# ── MAC 공용 계산 ─────────────────────────────────────────────

MAC_CARBON_PRICE = 20780
MAC_MIN, MAC_MAX = 15000, 26000
MAC_FALLBACK_YEAR = 2025   # 실데이터 없을 때 사용하는 기준연도


def _compute_all_mac(df, target_year, target_month):
    """
    target_year년 target_month월 기준 월별 동적 MAC 계산.

    각 시설별:
      소각량: 실데이터 있으면 실데이터, 없으면 예측 모델 출력값
      kWh/ton, Nm³/ton: 실데이터 있으면 실데이터, 없으면 과거 동월 평균
    4개 시설 동월 기준으로 정규화 → MAC 산정

    반환: {facility: {mac, is_sell, decision, ...}}
    """
    SCALE = 30000
    eff_rows = []

    for fac in FACILITIES:
        row = df[
            (df['facility'] == fac) &
            (df['year']     == target_year) &
            (df['month']    == target_month)
        ]

        if len(row) > 0:
            r = row.iloc[0]
            incin = float(r['incineration_ton']) if pd.notna(r['incineration_ton']) and float(r['incineration_ton']) > 0 else None
            if incin:
                kwh_per_ton  = float(r['electricity_kwh']) / incin if pd.notna(r['electricity_kwh']) else None
                lng_per_ton  = float(r['lng_nm3'])         / incin if pd.notna(r['lng_nm3'])         else None
                data_source  = '실데이터'
            else:
                incin = kwh_per_ton = lng_per_ton = None
                data_source = '예측'
        else:
            incin = kwh_per_ton = lng_per_ton = None
            data_source = '예측'

        # 실데이터 없으면 예측값으로 채움
        if incin is None:
            pred_incoming, _ = _predict_recursive(fac, target_year, target_month)
            past_rates = _get_same_month_past_rates(df, fac, target_year, target_month)
            rate = float(np.mean(list(past_rates.values()))) if past_rates else 1.0
            incin = pred_incoming * rate

        if kwh_per_ton is None or lng_per_ton is None:
            # 과거 동월 평균 에너지 효율
            past = df[
                (df['facility'] == fac) &
                (df['month']    == target_month) &
                (df['year']     <  target_year)
            ].copy()
            past = past[past['incineration_ton'] > 0]
            if len(past) > 0:
                past['kwh_per_ton'] = past['electricity_kwh'] / past['incineration_ton']
                past['lng_per_ton'] = past['lng_nm3']         / past['incineration_ton']
                kwh_per_ton = float(past['kwh_per_ton'].replace([np.inf, -np.inf], np.nan).dropna().mean())
                lng_per_ton = float(past['lng_per_ton'].replace([np.inf, -np.inf], np.nan).dropna().mean())
            else:
                kwh_per_ton = lng_per_ton = 0.0

        eff_rows.append({
            'facility':    fac,
            'incin_ton':   incin        if np.isfinite(incin)        else 0.0,
            'kwh_per_ton': kwh_per_ton  if np.isfinite(kwh_per_ton)  else 0.0,
            'lng_per_ton': lng_per_ton  if np.isfinite(lng_per_ton)  else 0.0,
            'data_source': data_source,
        })

    # ── 4개 시설 동월 기준 정규화 → MAC ────────────
    kwh_vals = [r['kwh_per_ton'] for r in eff_rows if r['kwh_per_ton'] > 0]
    lng_vals = [r['lng_per_ton'] for r in eff_rows if r['lng_per_ton'] > 0]

    kwh_min = min(kwh_vals) if kwh_vals else 0.0
    kwh_max = max(kwh_vals) if kwh_vals else 1.0
    lng_min = min(lng_vals) if lng_vals else 0.0
    lng_max = max(lng_vals) if lng_vals else 1.0

    result = {}
    for r in eff_rows:
        kwh_v = r['kwh_per_ton'] if r['kwh_per_ton'] > 0 else kwh_min
        lng_v = r['lng_per_ton'] if r['lng_per_ton'] > 0 else lng_min

        kwh_score = (kwh_v - kwh_min) / (kwh_max - kwh_min) if kwh_max > kwh_min else 0.0
        lng_score = (lng_v - lng_min) / (lng_max - lng_min) if lng_max > lng_min else 0.0
        ineff = kwh_score * 0.5 + lng_score * 0.5
        mac   = int(round(MAC_MAX - ineff * (MAC_MAX - MAC_MIN)))
        is_sell = mac < MAC_CARBON_PRICE

        result[r['facility']] = {
            'facility':    r['facility'],
            'monthly_incin': f"{r['incin_ton']:,.0f}",
            'elec_per_ton':  f"{r['kwh_per_ton']:,.1f}",
            'lng_per_ton':   f"{r['lng_per_ton']:,.2f}",
            'elec_score':    f"{kwh_score*100:.1f}",
            'lng_score':     f"{lng_score*100:.1f}",
            'ineff_score':   f"{ineff*100:.1f}",
            'mac':           f"{mac:,}",
            'mac_raw':       mac,
            'mac_bar_pct':   round(min(100, mac / SCALE * 100), 1),
            'cp_bar_pct':    round(MAC_CARBON_PRICE / SCALE * 100, 1),
            'is_sell':       is_sell,
            'decision':      '감축 후 판매 유리' if is_sell else '배출권 구매 유리',
            'gap':           f"{abs(mac - MAC_CARBON_PRICE):,}",
            'data_source':   r['data_source'],
        }
    return result


# ── MAC 분석 뷰 ──────────────────────────────────────────────

def mac_analysis(request):
    if 'member_no' not in request.session:
        return redirect('/')

    df = _load_facility_df()

    # 최신 실데이터 연도·월 기본값
    latest = df[['year', 'month']].drop_duplicates().sort_values(['year', 'month']).iloc[-1]
    default_year  = int(latest['year'])
    default_month = int(latest['month'])

    available_years = sorted(df['year'].unique().tolist(), reverse=True)

    try:
        sel_year  = int(request.GET.get('year',  default_year))
        sel_month = int(request.GET.get('month', default_month))
    except ValueError:
        sel_year, sel_month = default_year, default_month

    data = _compute_all_mac(df, sel_year, sel_month)
    rows = list(data.values())

    ctx = {
        'member_no':       request.session['member_no'],
        'member_name':     request.session['member_name'],
        'member_role':     request.session.get('member_role', 'member'),
        'sel_year':        sel_year,
        'sel_month':       sel_month,
        'available_years': available_years,
        'months':          list(range(1, 13)),
        'carbon_price':    f"{MAC_CARBON_PRICE:,}",
        'mac_min':         f"{MAC_MIN:,}",
        'mac_max':         f"{MAC_MAX:,}",
        'cp_bar_pct':      round(MAC_CARBON_PRICE / 30000 * 100, 1),
        'rows':            rows,
        'sell_count':      sum(1 for r in rows if r['is_sell']),
    }
    return render(request, 'mac.html', ctx)


# ── 반입량 + 소각량 + CO2 예측 뷰 ────────────────────────────

def predict_incoming(request):
    if 'member_no' not in request.session:
        return redirect('/')

    ctx = {
        'member_no':   request.session['member_no'],
        'member_name': request.session['member_name'],
        'member_role': request.session.get('member_role', 'member'),
        'facilities':  FACILITIES,
        'months':      list(range(1, 13)),
    }

    if request.method == 'POST':
        facility     = request.POST.get('facility', '').strip()
        target_year  = request.POST.get('target_year', '').strip()
        target_month = request.POST.get('target_month', '').strip()

        ctx['sel_facility']     = facility
        ctx['sel_target_year']  = target_year
        ctx['sel_target_month'] = target_month

        if facility not in FACILITIES:
            ctx['error'] = '시설을 선택해주세요.'
            return render(request, 'predict_incoming.html', ctx)

        try:
            target_year  = int(target_year)
            target_month = int(target_month)
        except ValueError:
            ctx['error'] = '연도와 월을 올바르게 입력하세요.'
            return render(request, 'predict_incoming.html', ctx)

        if not (2015 <= target_year <= 2035) or not (1 <= target_month <= 12):
            ctx['error'] = '연도(2015~2035)와 월(1~12)을 올바르게 입력하세요.'
            return render(request, 'predict_incoming.html', ctx)

        ctx['sel_target_year']  = target_year
        ctx['sel_target_month'] = target_month

        step = request.POST.get('step', '1')
        df = _load_facility_df()

        if step == '1':
            past_rates = _get_same_month_past_rates(df, facility, target_year, target_month)
            prev_year  = target_year - 1
            need_extra = prev_year not in past_rates
            auto_avg   = float(np.mean(list(past_rates.values()))) if past_rates else None

            ctx['show_rate_input'] = True
            ctx['auto_avg_rate']   = round(auto_avg * 100, 2) if auto_avg is not None else None
            ctx['past_years']      = sorted(past_rates.keys())
            ctx['need_extra']      = need_extra
            ctx['missing_year']    = prev_year
            ctx['missing_month']   = target_month

        else:
            # ① 소각비율 확정
            past_rates = _get_same_month_past_rates(df, facility, target_year, target_month)
            values = list(past_rates.values())

            extra_pct = request.POST.get('extra_rate_pct', '').strip()
            if extra_pct:
                try:
                    values.append(float(extra_pct) / 100)
                except ValueError:
                    ctx['error'] = '소각비율 값을 올바르게 입력하세요.'
                    return render(request, 'predict_incoming.html', ctx)

            if not values:
                ctx['error'] = '소각비율 계산에 필요한 데이터가 없습니다.'
                return render(request, 'predict_incoming.html', ctx)

            final_rate = float(np.mean(values))

            # ② 반입량 예측 (재귀)
            pred_incoming, predicted_months = _predict_recursive(facility, target_year, target_month)
            pred_incineration = pred_incoming * final_rate
            pred_co2 = pred_incineration * CO2_EMISSION_FACTOR

            ctx['pred_incoming']     = round(pred_incoming, 1)
            ctx['pred_rate']         = round(final_rate * 100, 2)
            ctx['pred_incineration'] = round(pred_incineration, 1)
            ctx['pred_co2']          = round(pred_co2, 1)
            ctx['co2_factor']        = round(CO2_EMISSION_FACTOR, 4)

            # ③ 탄소배출 허용량 배분
            allowances = _load_carbon_allowances()
            if target_year in allowances:
                annual_total_allowance = allowances[target_year]

                # 4개 시설 연간 소각량 추정
                annual_incins = {
                    fac: _estimate_annual_incin_ton(fac, target_year, df)
                    for fac in FACILITIES
                }
                total_incin = sum(annual_incins.values())

                if total_incin > 0:
                    fac_share = annual_incins[facility] / total_incin
                    monthly_allowance = annual_total_allowance * fac_share / 12
                    co2_diff = pred_co2 - monthly_allowance

                    ctx['annual_total_allowance'] = round(annual_total_allowance, 0)
                    ctx['fac_share_pct']          = round(fac_share * 100, 1)
                    ctx['monthly_allowance']      = round(monthly_allowance, 1)
                    ctx['co2_diff']               = round(co2_diff, 1)
                    ctx['co2_over']               = co2_diff > 0
                    # 시설별 연간 소각량 비교표
                    ctx['fac_incin_breakdown'] = [
                        {
                            'name': fac,
                            'annual_incin': round(annual_incins[fac], 0),
                            'share_pct': round(annual_incins[fac] / total_incin * 100, 1),
                        }
                        for fac in FACILITIES
                    ]

            # ④ MAC 연결: 예측 연도·월 기준 동적 MAC
            mac_data = _compute_all_mac(df, target_year, target_month)
            fac_mac  = mac_data.get(facility, {})
            ctx['mac'] = fac_mac

            if fac_mac and target_year in (allowances or {}):
                mac_raw = fac_mac['mac_raw']
                # 초과량 기준 의사결정 메시지
                co2_diff_raw = pred_co2 - (
                    allowances[target_year] *
                    (annual_incins.get(facility, 0) / total_incin) / 12
                    if total_incin > 0 else 0
                )
                if co2_diff_raw > 0:
                    # 초과 → 감축 or 구매?
                    if mac_raw < MAC_CARBON_PRICE:
                        advice_type = 'reduce'
                        advice_cost = round(co2_diff_raw * mac_raw / 10000, 0)
                        buy_cost    = round(co2_diff_raw * MAC_CARBON_PRICE / 10000, 0)
                        ctx['mac_advice'] = {
                            'type':       'reduce',
                            'msg':        f'초과 {round(co2_diff_raw, 1):,.1f} tCO₂를 직접 감축하는 것이 경제적',
                            'reduce_cost': f"{advice_cost:,.0f}만원",
                            'buy_cost':    f"{buy_cost:,.0f}만원",
                            'saving':      f"{round((buy_cost - advice_cost), 0):,.0f}만원",
                        }
                    else:
                        buy_cost    = round(co2_diff_raw * MAC_CARBON_PRICE / 10000, 0)
                        reduce_cost = round(co2_diff_raw * mac_raw / 10000, 0)
                        ctx['mac_advice'] = {
                            'type':        'buy',
                            'msg':         f'초과 {round(co2_diff_raw, 1):,.1f} tCO₂는 배출권 구매가 경제적',
                            'reduce_cost': f"{reduce_cost:,.0f}만원",
                            'buy_cost':    f"{buy_cost:,.0f}만원",
                            'saving':      f"{round((reduce_cost - buy_cost), 0):,.0f}만원",
                        }
                else:
                    surplus = abs(co2_diff_raw)
                    ctx['mac_advice'] = {
                        'type': 'surplus',
                        'msg':  f'허용량 이내 — 잉여 배출권 {surplus:,.1f} tCO₂ 판매 가능',
                        'sell_revenue': f"{round(surplus * MAC_CARBON_PRICE / 10000, 0):,.0f}만원",
                    }

            steps = [
                f'{y}년 {m}월  →  {v:,.0f} 톤 (예측)'
                for (y, m), v in sorted(predicted_months.items())
                if (y, m) != (target_year, target_month)
            ]
            ctx['steps'] = steps

    return render(request, 'predict_incoming.html', ctx)
