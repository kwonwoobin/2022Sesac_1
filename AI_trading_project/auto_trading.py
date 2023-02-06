import pymysql
import csv
import pandas as pd
import talib
import yaml
import numpy as np
import datetime
import time
import requests
import json
import operator
import datetime
import time
import os
from pytz import timezone
from pandas.io.stata import relativedelta
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import LSTM

def DL_make_dataset(data, label, window_size=20):
    feature_list = []
    label_list = []
    for i in range(len(data) - window_size):
        feature_list.append(np.array(data.iloc[i:i+window_size]))
        label_list.append(np.array(label.iloc[i+window_size]))
    return np.array(feature_list), np.array(label_list)


def deep_learning_model(code, window_size=20):
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()

    query0="SELECT * FROM daily_price WHERE date BETWEEN '2008-01-01' AND '2023-01-17'AND code={0} ORDER BY date".format(code)
    cur.execute(query0)
    datas = cur.fetchall()
    company = [data for data in datas] 
    df = pd.DataFrame(company)
    df.rename(columns = {0:'code', 2:'open', 3:'high', 4:'low', 5:'close', 6:'diff', 7:'volume'}, inplace = True)
    df_date = [df[1][i].strftime('%Y-%m-%d') for i in range(len(datas))]
    df = pd.concat([pd.DataFrame(df_date),df[['code','open','high','low','close','diff','volume']]], axis=1)
    df.rename(columns = {0:'date'}, inplace = True)

    query1 ="SELECT * FROM exchage_rate WHERE date BETWEEN '2008-01-01' AND '2023-01-17' ORDER BY date"
    cur.execute(query1)
    datas = cur.fetchall()
    df_exchange = [data for data in datas]
    df_exchange = pd.DataFrame(df_exchange)
    exchange_date = pd.DataFrame([df_exchange[0][i].strftime('%Y-%m-%d') for i in range(len(datas))])
    exchange_date.rename(columns={0:'date'}, inplace=True)
    rate = pd.DataFrame(float(df_exchange[1][i].replace(',','')) for i in range(len(datas)))
    rate.rename(columns={0:'exchange_rate'}, inplace=True)
    exchange = pd.concat([exchange_date,rate], axis=1)


    query2 ="SELECT * FROM interest_rate WHERE date BETWEEN '2008-01-01' AND '2023-01-17' ORDER BY date"
    cur.execute(query2)
    datas = cur.fetchall()
    df_interest = [data for data in datas]
    df_interest = pd.DataFrame(df_interest)
    interest_date = pd.DataFrame([df_interest[0][i].strftime('%Y-%m-%d') for i in range(len(datas))])
    interest_date.rename(columns={0:'date'}, inplace=True)
    rate = pd.DataFrame([float(df_interest[1][i].replace(',','')) for i in range(len(datas))])
    rate.rename(columns={0:'interest_rate'}, inplace=True)
    interest = pd.concat([interest_date,rate], axis=1)

    conn.commit()

    merge_df = pd.merge(df, exchange, how='left', on='date')
    merge_df = pd.merge(merge_df, interest, how='left', on='date')

    interest_rate_null_list = merge_df.loc[merge_df['interest_rate'].isnull()==True].index.tolist()
    for idx in interest_rate_null_list:
        rate = merge_df['interest_rate'].iloc[idx-1]
        merge_df['interest_rate'].iloc[idx] = rate

    exchange_rate_null_list = merge_df.loc[merge_df['exchange_rate'].isnull()==True].index.tolist()
    for idx in exchange_rate_null_list:
        rate = merge_df['exchange_rate'].iloc[idx-1]
        merge_df['exchange_rate'].iloc[idx] = rate

    # minmaxscaler 구현
    scale_cols = ['open', 'high', 'low', 'close', 'diff','volume', 'exchange_rate', 'interest_rate']
    scale_df = merge_df[scale_cols]
    min_ = scale_df.min(axis=0)
    max_ = scale_df.max(axis=0)
    scale_std = (scale_df - min_) / (max_ - min_)

    # test_size로 학습용, 테스트용 데이터 분리
    TEST_SIZE = int(len(scale_std) * 0.2)
    WINDOW_SIZE = window_size
    
    train = scale_std[:-TEST_SIZE]
    test = scale_std[-TEST_SIZE:]

    feature_cols = ['open', 'high', 'low', 'diff','volume', 'exchange_rate', 'interest_rate']
    label_cols = ['close']
    train_feature = train[feature_cols]
    train_label = train[label_cols]
    test_feature = test[feature_cols]
    test_label = test[label_cols]

    train_feature_after, train_label_after = DL_make_dataset(train_feature, train_label, window_size)

    x_train, x_valid, y_train, y_valid = train_test_split(train_feature_after, train_label_after, test_size=0.2)
    test_feature_after, test_label_after = DL_make_dataset(test_feature, test_label, window_size=window_size)
    # print('3')
    # print(x_train.shape, x_valid.shape, y_train.shape, y_valid.shape)

    #모델 선언
    model = Sequential()
    model.add(LSTM(16, 
                  input_shape=(train_feature_after.shape[1], train_feature_after.shape[2]), 
                  activation='relu', 
                  return_sequences=False)
              )

    model.add(Dense(1))

    #모델 학습시키기
    model.compile(loss='mean_squared_error', optimizer='adam')
    early_stop = EarlyStopping(monitor='val_loss', patience=5)

    model_path = 'model'
    filename = os.path.join(model_path, 'tmp_checkpoint.h5')
    checkpoint = ModelCheckpoint(filename, monitor='val_loss', verbose=1, save_best_only=True, mode='auto')
    history = model.fit(x_train, y_train, 
                                        epochs=5, 
                                        batch_size=250,
                                        validation_data=(x_valid, y_valid), 
                                        callbacks=[early_stop, checkpoint])
    
    model.load_weights(filename)
    pred = model.predict(test_feature_after)
    # score = model.evaluate(test_feature_after, test_label_after)
    # print('Test score:', score[0])
    # print('Test accuracy:', score[1])

    # 가격 minmaxscaler reverse
    test_label_reverse = test_label_after * (max_[3] - min_[3]) + min_[3]
    pred_reverse = pred * (max_[3] - min_[3]) + min_[3]
    open_reverse = test_feature['open'][-len(test_label_after):] * (max_[0] - min_[0]) + min_[0]

    # 합치기
    arr = np.concatenate([test_label_reverse, pred_reverse], axis=1)

    # result
    result_dict = {}
    for i in range(len(scale_std.index[-len(test_label_after):])):
        result_dict.update({df.index[-len(test_label_after):].values[i]:arr[i]})

    result = pd.DataFrame.from_dict(result_dict).T
    result.rename(columns={0:'test_close', 1:'predict'}, inplace=True)
    result['date'] = df['date']
    result['open'] = open_reverse
    result['code'] = str(df['code'][0]).zfill(6)

    return result

def DL_make_signal(model_result):
    
    df = model_result
    df.reset_index(drop=True, inplace=True)
    # df.rename(columns={'Unnamed: 0':'date'}, inplace=True)
    # print(df.index)

    label=[]
    for i in range(19,len(df)):
        if df['test_close'][i] < df['predict'][i]:
            label.append(1)
        elif df['test_close'][i] > df['predict'][i]:
            label.append(-1)
        elif df['test_close'][i] == df['predict'][i]:
            label.append(0)
    # print(label)
    df['label']=0
    df['label'][19:]=label
    

    signal=[]
    for i in range(19, len(df)):
        # 첫번째 거래이고
        if i== 19:
            # up이면 buy
            if df['label'][i]== 1:
                signal.append('1')
            # down이면 no action
            elif df['label'][i]== -1:
                signal.append('0')
        # up -> down : sell
        elif df['label'][i-1] == 1 and df['label'][i] == -1 :
            signal.append('2')
        # up -> up : holding
        elif df['label'][i-1] == 1 and df['label'][i] == 1 :
            signal.append('0')
        # down -> down : no action
        elif df['label'][i-1] == -1 and df['label'][i] == -1 :
            signal.append('0')
        # down -> up : buy
        elif df['label'][i-1] == -1 and df['label'][i] == 1 :
            signal.append('1')

    df['signal'] = 0
    df['signal'][19:] = signal

    # buy_sell 날짜, buy_sell 신호
    signal_buy_sell_date = []
    signal_buy_sell_signal=[]

    for idx, signal in enumerate(df['signal']):
        # buy 신호
        if signal == 'buy' or 'sell':       
            signal_buy_sell_date.append(df['date'][idx])
            signal_buy_sell_signal.append(df['signal'][idx])

    signal_buy_sell_date = pd.DataFrame(signal_buy_sell_date, columns=['ord_sig_dt'])
    signal_buy_sell_signal = pd.DataFrame(signal_buy_sell_signal, columns=['ord_sig'])
    df_signal = pd.concat([signal_buy_sell_date, signal_buy_sell_signal], axis =1)
    df_signal = df_signal[19:]    
    df_signal['iem_cd'] = str(df['code'][0]).zfill(6)
    df_signal['mod_id'] = 2
    df_signal = df_signal[['mod_id','ord_sig','ord_sig_dt','iem_cd']]
    df_signal = tuple(df_signal.iloc[-1].to_list())
    print(df_signal)
    return df_signal


def insert_mod_sign(signal_list):
    # DB에 쓰는 것
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()
    sql = f"INSERT INTO mod_sign(mod_id, ord_sig, ord_sig_dt, iem_cd) VALUES("+','.join(["%s"]*4)+");"
    cur.executemany(sql, signal_list)
    conn.commit()
    return signal_list

    

# 보유 현금 조회 -> # 주식 현재가 시세 조회 -># 주식 시장가 주문(현금)-> # 주식 현재가 체결 -> #보유자산확인 
with open('./DL_config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO'] # 계좌
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']



    
def hashkey(datas):
    """암호화"""
    PATH = "uapi/hashkey"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
    'content-Type' : 'application/json',
    'appKey' : APP_KEY,
    'appSecret' : APP_SECRET,
    }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))
    hashkey = res.json()["HASH"]
    return hashkey


#토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출
def get_current_price(code):
    """현재가 조회"""
    # 현재 기업별 주식 체크
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"FHKST01010100"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    #데이터 확인해보기(res.json()) 형태 결과값 사용해보기
    print(res.json()['output']['stck_prpr']) 
    return int(res.json()['output']['stck_prpr'])

def get_stock_balance():
    """주식 잔고조회(모델별 통합계좌 운용)"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"VTTC8434R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    print(res.json())
    stock_list = res.json()['output1']
    print(stock_list)
    evaluation = res.json()['output2']
    stock_dict = {}
    send_message(f"====주식 보유잔고====")
    # 값 확인해보기
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0:
            stock_dict[stock['pdno']] = stock['hldg_qty']
            send_message(f"{stock['prdt_name']}({stock['pdno']}): {stock['hldg_qty']}주")
            time.sleep(0.1)
    send_message(f"주식 평가 금액: {evaluation[0]['scts_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"평가 손익 합계: {evaluation[0]['evlu_pfls_smtl_amt']}원")
    time.sleep(0.1)
    send_message(f"총 평가 금액: {evaluation[0]['tot_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"=================")
    return stock_dict

def get_balance():
    """현금 잔고조회"""
    
    PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        # "tr_id":"TTTC8908R",  ## 실전투자
        "tr_id":"VTTC8908R", ## 모의투자
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": '005930',
        "ORD_UNPR": '700000',
        "ORD_DVSN": "00",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N",
    }
    print('prams까지함')
    print(URL)
    res = requests.get(URL, headers=headers, params=params)
    print('Get 됨')

    print(res.json())
    # 현금 잔고 조회
    cash = res.json()['output']['ord_psbl_cash']
    print('cash')
    send_message(f"주문 가능 현금 잔고: {cash}원")
    return int(cash)

# 주식 매수주문 요청 api
def buy(code, qty):
    """주식 시장가 매수 주문"""  
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    #body: 부분 해당
    # - ORD_DVSN: 주문구분 -> 01 : 시장가
    # - ORD_QTY: 주문수량 , 장전 시간외, 장후 시간외, 시장가의 경우 1주당 가격을 공란으로 비우지 않음 "0"으로 입력 권고
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": code,
        "ORD_DVSN": "01",
        "ORD_QTY": str(int(qty)),
        "ORD_UNPR": "0",
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"VTTC0802U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[매수 성공]{str(res.json())}")
        return True
    else:
        send_message(f"[매수 실패]{str(res.json())}")
        return False

# 주식 매도주문 요청 api
def sell(code, s_type, qty):
    """주식 시장가 매도"""
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": code,
        # 3시 30분 지나서 종가 코드 06(장후시간외)
        "ORD_DVSN": s_type,
        "ORD_QTY": qty,
        "ORD_UNPR": "0",
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"VTTC0801U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[매도 성공]{str(res.json())}")
        return True
    else:
        send_message(f"[매도 실패]{str(res.json())}")
        return False

# DB 업데이트 -> 결과값 조회
def inquire_model_balance(model):
    '''db 모델거래내역(mod_act) 테이블에 들어갈 값들을 튜플로 반환해주는 함수'''
    PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json",
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"VTTC8434R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()['output1']
    evaluation = res.json()['output2']
    print('eval : ', evaluation)

    mod_ren_dt = datetime.datetime.today().strftime('%Y-%m-%d') # 모델 업데이트 날짜

    # 1. 모델원금 db에서 조회
    where_condition_cash=[('mod_id', '=', model)]
    tot_mod_pri = float(select('tot_mod_pri', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_cash)[0][0])
    print('모델원금:',tot_mod_pri)
    
    # 수익금
    profit = int(evaluation[0]['tot_evlu_amt'])-10000000
    print('수익금: ' , profit)

    #수익률
    tot_mod_rtr = profit/10000000
    print('수익률', tot_mod_rtr)

    #모델수익금
    tot_mod_prf = tot_mod_pri*tot_mod_rtr
    print('수익:',tot_mod_prf)

    # 모델평가자산 = 원금+모델수익금
    tot_mod_inv = tot_mod_pri + tot_mod_prf
    print('모델평가자산',tot_mod_inv)
    
    # 보유비중 tot_mod_iem
    item_list=[]
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0: # 보유수량이 0보다 많으면
            print(int(stock['hldg_qty']))
            stock_dict = {}
            stock_dict['code'] = stock['pdno'] # 상품번호
            stock_dict['quantity'] = int(stock['hldg_qty']) # 보유주식수
            # 기업별 비중 구하기 : (기업별현재매입가*기업보유주식수)/평가금액
            price = int(stock['prpr']) #해당주식 현재가
            percent = (price*int(stock['hldg_qty']))/(tot_mod_pri+tot_mod_prf) #모델원금+수익금=평가자산
            stock_dict['percent'] = round(percent,3)
            item_list.append(stock_dict)
            time.sleep(0.1)
    # 현금비중 따로 딕셔너리를 리스트에 추가하기
    balance_dict={}
    balance = get_balance()
    try:
        tot_mod_mon_rtr = balance/int(tot_mod_inv) # 현금비중=(남은현금/평가금액)*100
    except:
        tot_mod_mon_rtr = 100
    balance_dict['code']='000000'
    balance_dict['percent']= tot_mod_mon_rtr
    item_list.append(balance_dict)
    tot_mod_iem = item_list
    # 홀딩금액 hold_pri은 다른 곳에서 처리
    return [('mod_id',model), ('mod_ren_dt','DATE_FORMAT("'+mod_ren_dt+'","%Y-%m-%d")'),('tot_mod_prf',tot_mod_prf),('tot_mod_inv',tot_mod_inv),('tot_mod_rtr',(tot_mod_rtr)*100),('tot_mod_iem',tot_mod_iem)]

# 주식일별주문체결조회
def inquire_daily_order(code):
    """db mod_trs 업데이트를 위해 값들을 api에서 조회하여 tuple형식으로 반환해주는 함수"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json",
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"VTTC8001R",
        "custtype":"P",
    }
    now = datetime.datetime.today().strftime('%Y%m%d')
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "INQR_STRT_DT": now, # 조회시작일자
        "INQR_END_DT": now, # 조회종료일자
        "SLL_BUY_DVSN_CD": "00", # 매도매수구분코드 - 전체(매도:1/매수:2 둘 다 가능)
        "INQR_DVSN": "01", # 정순
        "PDNO": code,
        "CCLD_DVSN": "00", # 체결구분 - 전체(매도매수 둘 다 가능)
        "ORD_GNO_BRNO": "", #주문채번지점번호 - null
        "ODNO": "", # 주문번호 : 주문시 한국투자증권 시스템에서 채번된 주문번호
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1":"",
        "CTX_AREA_FK100":"",
        "CTX_AREA_NK100":""
    }
    res = requests.get(URL, headers=headers, params=params)

    result = res.json()['output1']
    mod_id = 2
    ord_dt = result[0]['ord_dt']
    iem_cd = result[0]['pdno']
    sby_dit_cd = result[0]['sll_buy_dvsn_cd']
    cns_qty = result[0]['tot_ccld_qty']
    orr_pr = result[0]['tot_ccld_amt']

    return (mod_id, ord_dt, iem_cd, sby_dit_cd, cns_qty, orr_pr)

# 당일 주문한 기업리스트
def get_daily_order_list(code_list):
    daily_order_list = []
    for code in code_list:
        daily_result = inquire_daily_order(code)
        daily_order_list.append(daily_result)
    return daily_order_list

def get_rate_of_return():
    """종목 수익률별로 정렬해서 리스트로 반환하는 함수"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json",
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"VTTC8434R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()['output1']
    evaluation = res.json()['output2']
    print(stock_list)
    stock_dict = {}
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0: # 보유수량이 0보다 많으면
            stock_dict[stock['pdno']] = stock['evlu_erng_rt'] # 상품번호가 key, 평가수익률이 value
            time.sleep(0.1)
    stock_dict = sorted(stock_dict.items(), key=lambda x:x[1], reverse=True)
    return [stock[0] for stock in stock_dict]
# # 요청금액만큼 내림해서 매도 - 1)사용자보유기업조회 2)수익률 안좋은 기업부터 매도(리스트순서정렬) 3)사용자금액 충족될때까지 for문으로 돌리기
# # 08:40에 전날종가가격으로 일괄 매도

def process_user_withdrawal(model):
    # 사용자요청금액 확인
    where_condition=[('mod_id','=',model),('ord_cd','=',2),('prc_cd','=',0)]
    trs_check_list = select("*", 'trs_check', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition)
    
    # 리스트 하나라도 있어야 사용자매도 실시
    if len(trs_check_list) != 0:
        # 리스트 첫번째부터 처리
        for data in trs_check_list:
            prc_pri = data[6] # 요청금액
            index = data[0] # id 저장해놓기
            
            # 요청금액만큼 내림해서 매도
            # 1)사용자보유기업조회(usr_id로) - 수익률순으로 기업코드만 들어간 리스트로 반환
            stock_list = get_rate_of_return() # 보유 주식 조회(딕셔너리)
            total_sell_pri = 0 # 총매도금액
            for code in stock_list:
                # 해당 기업의 가격 조회 from DB
                where_condition_code = [('code', '=', code)]
                close_price = select("*", 'daily_price', limit=1, offset=None, order_by='id', DESC=True, where_condition=where_condition_code)[0][6]
                # qty 구하기 -> 사용자 요청금액 충족하면 stop
                qty = prc_pri // close_price
                print('사용자출금요청금액:',prc_pri)
                total_sell_pri += qty*close_price # 총매도금액에 추가
                prc_pri -= qty*close_price # 요청금액에 매도금액 빼기
                print( '주식가격:',close_price, '매도수량',qty)

            print('총매도금액:', total_sell_pri)
            # 평가자산 db에서 조회
            where_condition_eva = [('mod_id', '=', model)]
            eva_asset = int(select("tot_mod_inv", 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_eva)[0][0])
            
            # 매도금액/평가자산 퍼센트 -> 출금할 때 percent 안변하게 하려면 (1-percent_by_eva)해서 원금과 수익에 각각 곱해주기
            percent_by_eva = total_sell_pri/eva_asset
          
            # 모델원금 db에서 select
            where_condition_pri = [('mod_id', '=', model)]
            tot_mod_pri = int(select('tot_mod_pri', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_pri)[0][0])
            
            # 매도금액/평가자산 퍼센트를 원금이랑 수익에 곱해주고 그걸 db update
            tot_mod_pri = tot_mod_pri*(1-percent_by_eva)
            
            # 모델원금 update
            update('mod_act', 'tot_mod_pri', tot_mod_pri, 'mod_id', model)
            
            # 모델수익 db에서 select
            where_condition_prf = [('mod_id', '=', model)]
            tot_mod_prf = int(select('tot_mod_prf', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_prf)[0][0])
            tot_mod_prf = tot_mod_prf*(1-percent_by_eva)
            
            # 모델수익 db upate
            update('mod_act', 'tot_mod_prf', tot_mod_prf, 'mod_id', model)

            # 모델 평가자산 update = tot_mod_pri + tot_mod_prf
            tot_mod_inv = tot_mod_pri + tot_mod_prf
            update('mod_act', 'tot_mod_inv', tot_mod_inv, 'mod_id', model)

            # mod_ren_dt 업데이트
            mod_ren_dt = datetime.datetime.today().strftime('%Y-%m-%d')
            update('mod_act', 'mod_ren_dt', 'DATE_FORMAT("'+mod_ren_dt+'","%Y-%m-%d")', 'mod_id', model)
            print('날짜 업데이트 완료')

            # 남은 요청금액은 tb cap_act 출금금액으로 insert
            # 1) 남은 잔고 select해서 잔고금액 확인
            # 여유자금: surplus_balance
            where_condition_balance =  [('mod_id2','=',model)]
            surplus_balance = select('act_bal', 'cap_act', limit=1, offset=None, order_by='id', DESC=True, where_condition=where_condition_balance)[0][0]
            account = CANO+ACNT_PRDT_CD #계좌번호
            # 2) balance에 요청금액 빼기
            surplus_balance -= prc_pri

            # 3) cap_act테이블 insert
            # insert_remain_price(model, account, balance, prc_pri)
            now = datetime.datetime.now()
            values = [(model, account, now, surplus_balance, prc_pri)]
            print(values)
            insert_many('cap_act', 'mod_id2, cap_act, ren_dt, act_bal, wdr_pri', values)
            print('insert완료')
            # 4) 출금요청 완료하면 trs_check의 prc_cd(처리여부) 1로 update
            result = update('trs_check', 'prc_cd', 1, 'id', index)
            print('trs_check 업데이트결과:',result)

            print('-----------')

# 모델 선택한 유저들 업데이트
def update_users():
    send_message('update')
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()
    for i in range(1,3):
        # 최신 날짜 순 모델의 수익률 2개 추출(오늘, 어제 수익률)
        sql = "select tot_mod_rtr from mod_prf_info where mod_id = {} order by ren_dt desc limit 2".format(i)
        cur.execute(sql)
        conn.commit()
        rtr_data = []
        datas = cur.fetchall()
        for data in datas:
            rtr_data.append(data)
        today_rtr = rtr_data[0][0] - rtr_data[1][0]
        #print(today_rtr)
        #현재 유저들의 수익률 추출
        sql2 = "select * from usr_trn_info where mod_id = {}".format(i)
        cur.execute(sql2)
        conn.commit()
        usr_rtr_list = []
        # usr_id_list = []
        rtr_table_list = []
        datas = cur.fetchall()
        today = datetime.datetime.now()
        #print(today)
        for data in datas:
            #print(data)
            usr_id = data[1] #유저 아이디
            # usr_id_list.append(usr_id)
            rtr = data[7] + today_rtr #변동한 수익률
            cus_prf = (rtr * data[4]) / 100
            cus_inv = data[4] + cus_prf
            temp1 = [today,cus_prf, cus_inv, rtr, usr_id]
            temp2 = [usr_id, today, rtr]
            usr_rtr_list.append(temp1)
            rtr_table_list.append(temp2)
        # 해당 모델을 가진 유저들의 현재 수익률, 날짜 업데이트
        sql3 = "update usr_trn_info set ren_dt = %s , tot_cus_prf = %s, tot_cus_inv = %s, tot_cus_rtr = %s where mod_id = {} and usr_id = %s".format(i)
        cur.executemany(sql3, usr_rtr_list)
        conn.commit()
        # 수익률을 유저 수익률 테이블에 업데이트
        sql4 = "INSERT INTO usr_prf_info (usr_id, ren_dt, tot_cus_rtr) VALUE (%s, %s, %s)"
        cur.executemany(sql4,rtr_table_list)
        conn.commit()

def DL_calculation ():  
    send_message("계산 시작합니다")
    model = '2'
    # 보유주식조회
    stock_dict = get_stock_balance()
    # 보유한 주식 기업 코드 돌면서 list에 들어감 
    code_list = [code for code in stock_dict.keys()]
    # 장 마감 후 업데이트 해줘야 할 table: 모델거래내역 mod_trs, 모델자산내역 mod_act
    # mod_trs
    try:
        daily_order_list = get_daily_order_list(code_list)
        insert_many('mod_trs', 'mod_id, ord_dt, iem_cd, sby_dit_cd, cns_qty, orr_pr', daily_order_list)
    except:
        pass

    # 모델자산내역 mod_act테이블 update - 모델원금, 홀딩금액 빼고
    model_tuple = inquire_model_balance(model)
    # 안됨
    for data in model_tuple:
        if type(data[1])==list:
            data_1 = data[1]
            data_1 = '"'+str(data_1)+'"'
            update('mod_act', data[0], data_1, 'mod_id', model)
        else:
            update('mod_act', data[0], data[1], 'mod_id', model)
    # 1) mod_act에서 모델id, 업데이트날짜와 수se익률 select
    where_condition = [('mod_id', '=', model)]
    values = [select('mod_id, mod_ren_dt, tot_mod_rtr', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition)[0]]
    #((100,11,datetime,e),)
    # 2) 모델수익률테이블 mod_prf_info에 수익률 insert
    insert_many('mod_prf_info', 'mod_id, ren_dt, tot_mod_rtr', values)
    # db에서 기업 리스트 가져와서(get_company_list) increase_company 상승세인 기업 선정  
    company_list = get_company_list()
    increase_company = make_increase_company(company_list)
    # 보유 기업 조회해서 code_list에 추가
    # 5개로 정해서 sell한 기업 한정으로 기업 업데이트 하기

    max_com_count = 5
    if code_list != 5:
        additional_buy_count = max_com_count - len(code_list)
        # 추가로 매수할 종목 수
        if bool(increase_company) == False:
            pass
        else:
            for i in range(additional_buy_count):
                # 기업 같으면 pass
                if increase_company[i] in code_list:
                    pass
                code_list.append(increase_company[i])
    
    # 딥러닝 시그널 생성
    signal_list = []
    if bool(code_list) == False:
        pass
    else:
        for code in code_list:
            result = deep_learning_model(code)
            signal_list.append(DL_make_signal(result))
        # 생성된 매매신호 db(tb mod_sign) 업데이트
        insert_mod_sign(signal_list)
        send_message('signal_db 업데이트')

    send_message('계산 끝났습니다.')


def get_BSH_signal():
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()
    query = "SELECT * FROM mod_sign WHERE mod_id='2' ORDER BY id DESC LIMIT 5"
    cur.execute(query)
    conn.commit()
    datas = cur.fetchall()
    print(datas)
    buy_signal_list=[]
    sell_signal_list=[]
    hold_signal_list=[]
    for data in datas: # 전날 생성된 신호 조회
        print(data[2])
        print(data[4])
        signal = data[2]
        code = data[4]
        if signal == 1:
            buy_signal_list.append(code)
        elif signal== 2:
            sell_signal_list.append(code)
        elif signal== 0:
            hold_signal_list.append(code)

    return buy_signal_list, sell_signal_list, hold_signal_list


try:
    ACCESS_TOKEN = get_access_token()
    send_message("===국내 주식 자동매매 프로그램을 시작합니다===")

    model = '2'
    t_now = datetime.datetime.now()
    t_9 = t_now.replace(hour=11, minute=0, second=0, microsecond=0)
    t_exit = t_now.replace(hour=15, minute=00, second=0,microsecond=0)
    t_close_buy_exit = t_now.replace(hour=15, minute=30, second=0, microsecond=0)
    today = datetime.date.today()
    today_day = today.weekday()
    t_calculate_start = t_now.replace(hour=7, minute=0, second=0, microsecond=0)
    t_calculate_end = t_calculate_start + relativedelta(hours = 4)

    # 토요일이나 일요일이면 그 다음 월요일 자정이 되면 break
    if today_day < 5:

        # cron 장외 시간 계산: pm 6시(오전 1시-5시)
        if t_calculate_start < t_now < t_calculate_end:
            DL_calculation()
            print('DL_calculation 끝')
            update_users()
            print('update_users 끝')

        # 사용자 요청시 9시에 전날 종가 매도(cron:9시)
        # AM 09:00 - 장 끝나는 시간
        elif t_9 < t_now < t_exit:
            send_message('사용자출금요청 확인 후 전날 종가로 매도')
            process_user_withdrawal(model)
            send_message('출금요청 처리 완료')

            # 바로 매수 시작
            send_message('매수시작!')
            process_user_withdrawal(model) # 사용자가 원하면 매도
            stock_dict = get_stock_balance() # 보유 주식 조회(딕셔너리)
            # api잔고조회 -> holding금액 빼주기
            present_balance = get_balance() # api잔고조회
            present_balance = present_balance - (present_balance * 0.25)
            send_message('남은 잔고 가져오기 완료!')

            buy_signal_list, sell_signal_list, hold_signal_list = get_BSH_signal()
            send_message('signal 가져오기!')
            if len(buy_signal_list) != 0:
                target_buy_count = len(buy_signal_list) #매수할 종목 수
                buy_percent = round(1/target_buy_count, 3) # 종목당 매수 금액 비율
                buy_amount = present_balance*buy_percent  # 종목별 주문 금액 계산
            
            # 보유주식없고 매수신호 없는 경우
            if stock_dict == False and buy_signal_list==[]:
                pass
            # 사용자 요청시 8시 40분에 전날 종가 매도
            # 8시에 DB에 업데이트된 사용자 요청 처리
            else:
                # 잔고 부족하면 프로그램 종료
                for code in buy_signal_list:
                    current_price = get_current_price(code) # 해당 주식 현재가 조회
                    if present_balance < current_price:
                        break
                    buy_qty = 0  # 매수할 수량 초기화
                    buy_qty = int(buy_amount // current_price)
                    result = buy(code, buy_qty)
                    time.sleep(1)
                    # 잔고, 보유수량 업데이트할 필요 없음 - api로 조회                   
            pass

        # 3:00 - PM 3:30 : 신호 매도면 종가가격으로 매도(cron 오후 3시)
        elif t_exit < t_now < t_close_buy_exit:
            # time.sleep(144000)
            send_message('매도 시작합니다.')
            stock_dict = get_stock_balance()
            buy_signal_list, sell_signal_list, hold_signal_list = get_BSH_signal()
            for code in sell_signal_list:
                if code in stock_dict.keys():
                  qty = stock_dict[code] # 보유 주식 수
                  print('보유주식수:', qty)
                  result = sell(code, '01', qty)
                  print('result')
                  time.sleep(1)
                  send_message('매도 끝났습니다.')
                else:
                  send_message('sell리스트의 주식 현재 보유중 아닙니다. 프로그램 종료')
            pass

except Exception as e:
    print(e)
    send_message(f"[오류 발생]{e}")
    time.sleep(1)
