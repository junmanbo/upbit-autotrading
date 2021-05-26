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
def save_info():
    logging.info('그래프 분석 후 저장')
    for ticker in tickers:
        # 일봉 데이터 수집
        df = pyupbit.get_ohlcv(ticker, interval="day")

        # Save Stochastic Oscilator information
        info[ticker]['slow_osc'] = indi.calStochastic(df, 12, 5, 5)[0]
        info[ticker]['slow_osc_slope'] = indi.calStochastic(df, 12, 5, 5)[1]
        info[ticker]['macd_osc'] = indi.calMACD(df, 12, 26, 9)
        info[ticker]['ma'] = indi.calMA(df, 14)
        time.sleep(0.1)
    logging.info('그래프 분석 후 저장 완료')

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

bot.sendMessage(chat_id = chat_id, text=f"단타 전략 시작")

while True:
        now = datetime.datetime.now()
        time.sleep(1)
        if now.hour == 9 and now.minute == 0 and 0 <= now.second <= 2:
            save_info()
            free_balance = float(upbit.get_balances()[0]['balance']) # 계좌 잔고 조회
            money = adjust_money(free_balance) # 1코인당 투자 금액 설정
            for ticker in tickers:
                try:
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
                        time.sleep(1)
                        target_price = current_price * profit
                        info[ticker]['price'] = current_price
                        info[ticker]['position'] = 'long' # 포지션 'long' 으로 변경
                        info[ticker]['amount'] = amount # 코인 갯수 저장
                        current_hold += 1
                        bot.sendMessage(chat_id = chat_id, text=f"코인: {ticker}\n매수가: {current_price}\n투자금액: {money:.2f}\n총 보유 코인: {current_hold}")
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(e)
                    bot.sendMessage(chat_id = chat_id, text=f"에러발생 {e}")
            tickers = pyupbit.get_tickers("KRW")

        else:
            for ticker in tickers:
                try:
                    current_price = pyupbit.get_current_price(ticker) # 코인 현재가
                    if info[ticker]['position'] == 'wait':
                        tickers.remove(ticker)
                    elif info[ticker]['position'] == 'long' and current_price > info[ticker]['price'] * profit:
                        total_hold -= 1
                        info[ticker]['position'] = 'wait'
                        order = upbit.sell_market_order(ticker, info[ticker]['amount'])
                        bot.sendMessage(chat_id = chat_id, text=f"코인: {ticker}\n매수가: {info[ticker]['price']} -> 매도가: {info[ticker]['price']*profit}\n수익률: {(profit-1)*100:.2f}%")
                        logging.info(f"코인: {ticker} (롱) 포지션\n매수가: {info[ticker]['price']} -> 매도가: {info[ticker]['price']*profit}\n수익률: {profit:.2f}")
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(e)
                    bot.sendMessage(chat_id = chat_id, text=f"에러발생 {e}")
            with open('./Data/info.txt', 'w') as f:
                f.write(json.dumps(info)) # use `json.loads` to do the reverse

