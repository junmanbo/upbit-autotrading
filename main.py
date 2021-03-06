#!/usr/bin/env python

import pyupbit
import datetime
import time
import telegram
import logging
import json
from myPackage import indicators as indi

# 원하는 대로 수정 가능한 변수 값
money = 0
total_hold = 3 # 투자할 코인 갯수
profit = 1.015 # 익절 수익률(1.015 == 1.5%)

logging.basicConfig(filename='./Log/trading.log', format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

# 객체 생성
with open('./Api/upbit.txt') as f:
    lines = f.readlines()
    access = lines[0].strip()
    secret = lines[1].strip()
upbit = pyupbit.Upbit(access, secret)

# telegram setting
with open('./Api/mybot.txt') as f:
    lines = f.readlines()
    my_token = lines[0].strip()
    chat_id = lines[1].strip()
bot = telegram.Bot(token = my_token)

# Coin정보 저장 파일 불러오기
with open('./Data/info.txt', 'r') as f:
    data = f.read()
    info = json.loads(data)


# 코인별 Stochastic OSC 값 info에 저장
def save_info(ticker):
    # 일봉 데이터 수집
    df = pyupbit.get_ohlcv(ticker, interval="day")
    info[ticker]['slow_osc'] = indi.calStochastic(df, 12, 5, 5)[0]
    info[ticker]['slow_osc_slope'] = indi.calStochastic(df, 12, 5, 5)[1]
    info[ticker]['macd_osc'] = indi.calMACD(df, 12, 26, 9)
    info[ticker]['ma'] = indi.calMA(df, 14)

# 투자금액 조정
def adjust_money(free_balance):
    if current_hold < total_hold:
        available_hold = total_hold - current_hold
        money = round((free_balance / available_hold - 10000), 0)
        return money

# 지정가 예약 주문 취소
def cancel_order(ticker):
    try:
        ret = upbit.get_order(ticker)[0].get('uuid')
        order = upbit.cancel_order(ret)
        logging.info(f"{ticker}의 미체결된 거래내역을 취소했습니다.\n주문조회: {ret}\n취소내역: {order}")
    except:
        pass

tickers = pyupbit.get_tickers("KRW")

current_hold = 0
for ticker in tickers:
    if info[ticker]['position'] != 'wait':
        current_hold += 1 # 투자한 Coin 갯수

while True:
        now = datetime.datetime.now()
        time.sleep(1)
        if (now.hour + 3) % 6 == 0 and now.minute == 0 and 0 <= now.second <= 2:
            bot.sendMessage(chat_id = chat_id, text=f"단타 전략 시작\n조건에 맞는 코인 검색중")
            free_balance = float(upbit.get_balances()[0]['balance']) # 계좌 잔고 조회
            money = adjust_money(free_balance) # 1코인당 투자 금액 설정
            for ticker in tickers:
                try:
                    save_info(ticker)
                    current_price = pyupbit.get_current_price(ticker) # 코인 현재가
                    # 롱 포지션 청산
                    if info[ticker]['position'] == 'long':
                        current_hold -= 1
                        info[ticker]['position'] = 'wait'
                        cancel_order(ticker=ticker) # 예약 매도 주문 취소
                        time.sleep(1)
                        order = upbit.sell_market_order(ticker=ticker, volume=info[ticker]['amount']) # 시장가 매도
                        logging.info(f'주문 내역: {order}')
                        calProfit = (current_price - info[ticker]['price']) / info[ticker]['price'] * 100 # 수익률 계산
                        bot.sendMessage(chat_id = chat_id, text=f"코인: {ticker}\n매수가: {info[ticker]['price']} -> 매도가: {current_price}\n수익률: {calProfit:.2f}%")

                    # 조건 만족시 롱 포지션
                    elif current_hold < total_hold and info[ticker]['position'] == 'wait' and \
                            info[ticker]['slow_osc'] > 0 and info[ticker]['slow_osc_slope'] > 0 and \
                            info[ticker]['macd_osc'] > 0 and info[ticker]['open'] > info[ticker]['ma']:
                        amount = money / current_price # 거래할 코인 갯수
                        order = upbit.buy_market_order(ticker=ticker, price=money) # 시장가 매수
                        logging.info(f'주문 내역: {order}')
                        info[ticker]['price'] = current_price
                        info[ticker]['position'] = 'long' # 포지션 'long' 으로 변경
                        info[ticker]['amount'] = amount # 코인 갯수 저장
                        current_hold += 1
                        bot.sendMessage(chat_id = chat_id, text=f"코인: {ticker}\n매수가: {current_price}\n투자금액: {money:.2f}\n총 보유 코인: {current_hold}")
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(e)
                    bot.sendMessage(chat_id = chat_id, text=f"에러발생 {e}")
        elif current_hold != 0:
            for ticker in tickers:
                try:
                    if info[ticker]['position'] =='long': # 쓸데없이 현재가 조회하는 것을 막기 위해 따로 분리
                        current_price = pyupbit.get_current_price(ticker) # 코인 현재가
                        if current_price > info[ticker]['price'] * profit:
                            order = upbit.sell_market_order(ticker, info[ticker]['amount'])
                            calProfit = (current_price - info[ticker]['price']) / info[ticker]['price'] * 100 # 수익률 계산
                            total_hold -= 1
                            info[ticker]['position'] = 'wait'
                            bot.sendMessage(chat_id = chat_id, text=f"코인: {ticker}\n수익률: {calProfit:.2f}%")
                        time.sleep(1)
                except Exception as e:
                    logging.error(e)
                    bot.sendMessage(chat_id = chat_id, text=f"에러발생 {e}")
            with open('./Data/info.txt', 'w') as f:
                f.write(json.dumps(info))
