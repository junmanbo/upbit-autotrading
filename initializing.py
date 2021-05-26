#!/usr/bin/env python

import pyupbit
import json
import os

tickers = pyupbit.get_tickers("KRW")

# 코인별 저장 정보값 초기화
info = {}
for ticker in tickers:
    info[ticker] = {}
    info[ticker]['amount'] = 0 # 코인 매수/매도 갯수
    info[ticker]['position'] = 'wait' # 현재 거래 포지션 (long / short / wait)
    info[ticker]['price'] = 0 # 코인 거래한 가격
    info[ticker]['slow_osc'] = 0 # Stochastic Slow Oscilator 값 (Day)
    info[ticker]['slow_osc_slope'] = 0 # Stochastic Slow Oscilator 기울기 값 (Day)
    info[ticker]['macd_osc'] = 0 # MACD Oscilator 값
    info[ticker]['ma'] = 0 # 지수이동평균 값
    info[ticker]['open'] = 0 # 지수이동평균 값

with open('./Data/info.txt', 'w') as f:
    f.write(json.dumps(info)) # use `json.loads` to do the reverse
