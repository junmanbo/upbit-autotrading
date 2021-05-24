#!/usr/bin/env python

import pyupbit
import numpy as np
import pandas as pd
import datetime
import time
import telegram
import logging
import json
import os

# 경로 설정
home = os.getcwd()
path_log = os.path.join(home, 'logs', 'upbit_trading.log')
path_info = os.path.join(home, 'symmetrical-umbrella', 'info.txt')
path_upbit = os.path.join(home, 'api', 'upbit.txt')
path_telegram = os.path.join(home, 'api', 'mybot.txt')

logging.basicConfig(filename=path_log, format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

# 객체 생성
with open(path_upbit) as f:
    lines = f.readlines()
    access = lines[0].strip()
    secret = lines[1].strip()
upbit = pyupbit.Upbit(access, secret)

start_balance = upbit.get_balance("KRW")
end_balance = upbit.get_balance("KRW")

# telegram setting
with open(path_telegram) as f:
    lines = f.readlines()
    my_token = lines[0].strip()
    chat_id = lines[1].strip()
bot = telegram.Bot(token = my_token)

# Coin정보 저장 파일 불러오기
with open(path_info, 'r') as f:
    data = f.read()
    info = json.loads(data)

# Stochastic Slow Oscilator 값 계산
def calStochastic(df, n=12, m=5, t=5):
    ndays_high = df.high.rolling(window=n, min_periods=1).max()
    ndays_low = df.low.rolling(window=n, min_periods=1).min()
    fast_k = ((df.close - ndays_low) / (ndays_high - ndays_low)) * 100
    slow_k = fast_k.ewm(span=m).mean()
    slow_d = slow_k.ewm(span=t).mean()
    slow_osc = slow_k - slow_d
    slow_osc_slope = slow_osc - slow_osc.shift(1)
    df['slow_osc'] = slow_osc
    df['slow_osc_slope'] = slow_osc_slope
    return df['slow_osc'][-1], df['slow_osc_slope'][-1]

def calMA(df, fast=14):
    df['ma'] = df['close'].ewm(span=fast).mean()
    return df['ma'][-1]

def calMACD(df, m_NumFast=14, m_NumSlow=30, m_NumSignal=10):
    EMAFast = df.close.ewm( span = m_NumFast, min_periods = m_NumFast - 1 ).mean()
    EMASlow = df.close.ewm( span = m_NumSlow, min_periods = m_NumSlow - 1 ).mean()
    MACD = EMAFast - EMASlow
    MACDSignal = MACD.ewm( span = m_NumSignal, min_periods = m_NumSignal - 1 ).mean()
    df['macd_osc'] = MACD - MACDSignal
    return df['macd_osc'][-1]

# 코인별 Stochastic OSC 값 info에 저장
def save_info():
    logging.info('그래프 분석 후 저장')
    for ticker in tickers:
        # 일봉 데이터 수집
        df = pyupbit.get_ohlcv(ticker, interval="day")

        # Save Stochastic Oscilator information
        info[ticker]['slow_osc'] = calStochastic(df)[0]
        info[ticker]['slow_osc_slope'] = calStochastic(df)[1]
        info[ticker]['macd_osc'] = calMACD(df)
        info[ticker]['ma'] = calMA(df)
        info[ticker]['open'] = df['open'][-1]

        logging.info(f"코인: {ticker}\n\
            Stochastic OSC (Day): {info[ticker]['slow_osc']}\n\
            Stochastic OSC Slope (Day): {info[ticker]['slow_osc_slope']}\n\
            MACD: {info[ticker]['macd_osc']}\n\
            EMA: {info[ticker]['ma']}\n\
            OPEN: {info[ticker]['open']}\n")
        time.sleep(0.1)
    logging.info('그래프 분석 후 저장 완료')

# 투자금액 조정
def adjust_money(free_balance, total_hold):
    if total_hold < 3: # 투자 할 종목 갯수(total_hold)
        available_hold = 3 - total_hold
        money = round((free_balance / available_hold - 10000), 0)
        return money

# 지정가 예약 주문 취소
def cancel_order(ticker):
    try:
        ret = upbit.get_order(ticker)[0].get('uuid')
        upbit.cancel_order(ret)
        print(f"{ticker}의 미체결된 거래내역을 취소했습니다.")
    except:
        pass

# 호가 단위 맞추기
def price_unit(price):
    if price < 10:
        price = round(price, 2)
    elif 10 <= price < 100:
        price = round(price, 1)
    elif 100 <= price < 1000:
        price = round(price)
    elif 1000 <= price < 100000:
        price = round(price, -1)
    elif 100000 <= price < 1000000:
        price = round(price, -2)
    elif price >= 1000000:
        price = round(price, -3)
    return price


tickers = pyupbit.get_tickers("KRW")

total_hold = 0
for ticker in tickers:
    if info[ticker]['position'] != 'wait':
        total_hold += 1 # 투자한 Coin 갯수

money = 0
profit = 1.015 # 익절 수익률(1.015 == 1.5%)
bot.sendMessage(chat_id = chat_id, text=f"Stochastic (단타) 전략 시작합니다. 화이팅!")

#  except_coin = ['KRW-BTC', 'KRW-ETH'] # 거래에서 제외하고 싶은 코인(있으면 주석 풀고 추가)
#  for coin in except_coin:
#      tickers.remove(coin)

while True:
    try:
        now = datetime.datetime.now()
        time.sleep(1)
        if now.hour == 9 and now.minute == 0 and 30 <= now.second <= 33:
            save_info()
            free_balance = float(upbit.get_balances()[0]['balance'])
            money = adjust_money(free_balance, total_hold)
            for ticker in tickers:
                current_price = pyupbit.get_current_price(ticker)
                # 롱 포지션 청산
                if info[ticker]['position'] == 'long':
                    total_hold -= 1
                    info[ticker]['position'] = 'wait'
                    cancel_order(ticker=ticker) # 예약 매도 주문 취소
                    time.sleep(1)
                    order = upbit.sell_market_order(ticker=ticker, volume=info[ticker]['amount']) # 시장가 매도
                    calProfit = (current_price - info[ticker]['price']) / info[ticker]['price'] * 100 # 수익률 계산
                    bot.sendMessage(chat_id = chat_id, text=f"(단타){ticker} (롱)\n매수가: {info[ticker]['price']} -> 매도가: {current_price}\n수익률: {calProfit:.2f}%")
                    logging.info(f"코인: {ticker} (롱) 포지션 청산\n매수가: {info[ticker]['price']} -> 매도가: {current_price}\n수익률: {calProfit:.2f}")

                # 조건 만족시 롱 포지션
                elif total_hold < 3 and info[ticker]['position'] == 'wait' and \
                        info[ticker]['slow_osc'] > 0 and info[ticker]['slow_osc_slope'] > 0 and \
                        info[ticker]['macd_osc'] > 0 and info[ticker]['open'] > info[ticker]['ma']:
                    amount = money / current_price # 거래할 코인 갯수
                    order = upbit.buy_market_order(ticker=ticker, price=money) # 시장가 매수
                    time.sleep(1)
                    target_price = current_price * profit
                    target_price = price_unit(target_price)
                    order = upbit.sell_limit_order(ticker=ticker, price=target_price, volume=amount)
                    info[ticker]['price'] = current_price
                    info[ticker]['position'] = 'long' # 포지션 'long' 으로 변경
                    info[ticker]['amount'] = amount # 코인 갯수 저장
                    total_hold += 1
                    bot.sendMessage(chat_id = chat_id, text=f"(단타){ticker} 롱 포지션\n매수가: {current_price}\n투자금액: {money:.2f}\n총 보유 코인: {total_hold}")
                    logging.info(f"{ticker} 롱 포지션\n매수가: {current_price}\n투자금액: {money:.2f}\n총 보유 코인: {total_hold}")
                time.sleep(0.1)

        elif now.minute == 59 and 0 <= now.second <= 3:
            for ticker in tickers:
                df = pyupbit.get_ohlcv(ticker, interval="day")
                high = df['high'][-1]
                # 익절한 코인 체크
                if info[ticker]['position'] == 'long' and high > info[ticker]['price'] * profit:
                    total_hold -= 1
                    info[ticker]['position'] = 'wait'
                    bot.sendMessage(chat_id = chat_id, text=f"(단타){ticker} (롱)\n매수가: {info[ticker]['price']} -> 매도가: {info[ticker]['price']*profit}\n수익률: {(profit-1)*100}%")
                    logging.info(f"코인: {ticker} (롱) 포지션\n매수가: {info[ticker]['price']} -> 매도가: {info[ticker]['price']*profit}\n수익률: {profit}")
                time.sleep(0.1)
            with open(path_info, 'w') as f:
                f.write(json.dumps(info)) # use `json.loads` to do the reverse

    except Exception as e:
        logging.error(e)
        bot.sendMessage(chat_id = chat_id, text=f"에러발생 {e}")
