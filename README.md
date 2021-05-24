# symmetrical-umbrella

Auto Trading for Upbit (Short-Term)

## 업비트용 단기 투자 봇 입니다 (연습용)

- 본 전략은 Stochastic (기본값 - 12, 5, 5) slow %k 와 %d 를 이용한 Oscillator (Cross 구간) 값을 구합니다.
- 당일의 Oscillator 값과 전일의 Oscillator 값의 차로 기울기를 구합니다. (좀 더 반응이 빨라집니다.)
- 두 값이 양수일 때 매수 합니다.
- 매수와 동시에 이익실현 (기본값 - 1.5%) 로 지정가 매도를 진행합니다.
- 매일 아침 9시에 모든 보유한 코인을 매도 하고 조건을 체크하여 매수를 진행합니다.

### 설치 (Installation)

```bash
git clone https://github.com/mirae707/symmetrical-umbrella
```

### 준비 (Requirement)

- 모듈 설치

```bash
pip install --upgrade pip
pip install pyupbit python-telegram-bot numpy pandas
```

- api 키 저장 폴더 및 로그 저장 폴더 생성

```bash
mkdir -p ~/api
mkdir -p ~/logs
```

- api 키 저장
(업비트) 첫 번째 줄에는 Public 키 두 번째 줄에는 Secret 키를 입력하세요.  
(텔레그램) 첫 번째 줄에는 API 키 두 번째 줄에는 Chat ID 를 입력하세요.

```bash
cat > ~/api/upbit.txt << EOF
upbit public key
upbit secret key
EOF

cat > ~/api/mybot.txt << EOF
telegram api key
telegram chat id
EOF
```

위의 key 와 id 부분은 본인의 것으로 대체하여 입력하세요.

- 파이썬 파일 실행 권한 부여

```bash
chmod +x ~/symmetrical-umbrella/main.py
chmod +x ~/symmetrical-umbrella/initializing.py
```

- 코인에 저장할 정보 값 초기화하여 파일로 저장
Dictionary 형태로 코인 마다 (가격, Stochastic 수치, 매수량 등) 정보를 저장합니다.  
처음 사용하신다면 initializing.py 프로그램을 이용하여 초기화를 진행하시고  
그 외의 경우에는 저장된 정보로 계속 이용하시면 됩니다.

```bash
~/symmetrical-umbrella/initializing.py
```

### 실행 (Run)

- 서비스 등록 (자동 실행)
프로그램을 쉽게 실행하고 재부팅시에도 자동으로 실행하도록 설정합니다.

```bash
sudo cat > /etc/systemd/system/trading-upbit.service << EOF
[Unit]
Description=Algorithm Trading Bot for Upbit (Stochastic Short-Term Strategy)

[Service]
Type=simple
ExecStart=/home/user/symmetrical-umbrella/main.py
WorkingDirectory=/home/user
Restart=on-failure
User=user
Group=user

[Install]
WantedBy=multi-user.target
EOF
```

- 서비스 (실행, 정지, 재실행, 자동실행, 변경사항 업데이트)

```bash
sudo systemctl start trading-upbit.service # 서비스 실행
sudo systemctl stop trading-upbit.service # 서비스 정지
sudo systemctl restart trading-upbit.service # 서비스 재실행
sudo systemctl enable trading-upbit.service # 서비스 자동실행 등록
sudo systemctl daemon-reload # 서비스 변경사항 업데이트
```

성투하세요!  

## 투자 유의사항

1. 투자는 본인의 판단과 책임  

    - 투자는 반드시 자기 자신의 판단과 책임하에 하여야 하며, 자신의 여유자금으로 분산투자하는 것이 좋습니다.
    - 투자원금의 보장 또는 손실보전 약속은 법률적으로 효력이 없습니다.

2. 높은 수익에는 높은 위험
    - 높은 수익에는 반드시 높은 위험이 따른다는 것을 기억하고 투자시 어떤 위험이 있는지 반드시 확인하시기 바랍니다.  

3. 계좌관련 정보, API KEY 등은 본인이 직접 관리
    - 거래소 API KEY, 비밀번호, 텔레그램 API, 인증번호 등을 남에게 알리면 절대 안됩니다.

4. 매매거래에 이상이 있는지 수시로 확인
    - 매매체결 또는 거래 내역을 살펴보아 매매거래에 이상이 있는 경우 즉시 거래를 중단하셔야 합니다.
