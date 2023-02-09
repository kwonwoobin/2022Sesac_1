import datetime
import requests
import yaml
import json
import time
import pymysql
import pandas as pd
import talib
import datetime
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

with open('./DL_config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO'] # 계좌
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']


def get_access_token():
    """토큰 발급"""
    # 토큰 발급 매일 달라짐 실행하기 전에 한 번 해줘야 함. 
    headers = {"content-type":"application/json"}
    body = {"grant_type":"client_credentials",
    "appkey":APP_KEY, 
    "appsecret":APP_SECRET}
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    ACCESS_TOKEN = res.json()["access_token"]
    return ACCESS_TOKEN
ACCESS_TOKEN = get_access_token()
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
            # 기업별 비중 구하기 : (기업별매입가*기업보유주식수)/평가금액
            # pchs_avg_pric = float(stock['pchs_avg_pric']) # 매입평균가격
            price = int(stock['prpr']) #해당주식 현재가
            print('현재가:',price)
            print('분모 : ',tot_mod_pri+tot_mod_prf)
            print('분자 :', price*int(stock['hldg_qty']))
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
    mod_id = '1'
    ord_dt = result[0]['ord_dt']
    iem_cd = result[0]['pdno']
    sby_dit_cd = result[0]['sll_buy_dvsn_cd']
    cns_qty = result[0]['tot_ccld_qty']
    orr_pr = result[0]['tot_ccld_amt']

    return (mod_id, ord_dt, iem_cd, sby_dit_cd, cns_qty, orr_pr)


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
    
    stock_dict = {}
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0: # 보유수량이 0보다 많으면
            stock_dict[stock['pdno']] = stock['evlu_erng_rt'] # 상품번호가 key, 평가수익률이 value
            time.sleep(0.1)
    stock_dict = sorted(stock_dict.items(), key=lambda x:x[1], reverse=True)
    print('종목 수익률별로 정렬한 리스트:', [stock[0] for stock in stock_dict])
    return [stock[0] for stock in stock_dict]
# # 요청금액만큼 내림해서 매도 - 1)사용자보유기업조회 2)수익률 안좋은 기업부터 매도(리스트순서정렬) 3)사용자금액 충족될때까지 for문으로 돌리기
# # 08:40에 전날종가가격으로 일괄 매도




def process_user_withdrawal(model):
    # 사용자요청금액 확인
    print('사용자 요청금액 확인 시작')
    where_condition=[('mod_id','=',model),('ord_cd','=',2),('prc_cd','=',0)]
    trs_check_list = select("*", 'trs_check', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition)
    print('사용자 요청금액 확인 완료')

    # 리스트 하나라도 있어야 사용자매도 실시
    if len(trs_check_list) != 0:
        # 리스트 첫번째부터 처리
        print('사용자 출금요청 첫번째부터 처리')
        for data in trs_check_list:
            prc_pri = data[6] # 요청금액
            index = data[0] # id 저장해놓기
            
            # 요청금액만큼 내림해서 매도
            # 1)사용자보유기업조회(usr_id로) - 수익률순으로 기업코드만 들어간 리스트로 반환
            stock_list = get_rate_of_return() # 보유 주식 조회(딕셔너리)
            total_sell_pri = 0 # 총매도금액

            for code in stock_list:
                # 해당 기업의 가격 조회 from DB -> 이걸 현재가 조회해야할 듯?
                where_condition_code = [('code', '=', code)]
                close_price = select("close", 'daily_price', limit=1, offset=None, order_by='date', DESC=True, where_condition=where_condition_code)[0][0]

                # qty 구하기 -> 사용자 요청금액 충족하면 stop
                qty = prc_pri // close_price
                print('사용자출금요청금액:',prc_pri)
                total_sell_pri += qty*close_price # 총매도금액에 추가
                prc_pri -= qty*close_price # 요청금액에 매도금액 빼기
                print( '주식가격:',close_price, '매도수량',qty)
                # 해당 기업 qty만큼 매도하기 - 장전시간외(전일종가)
                # sell(code, "05", qty)
            print('총매도금액:', total_sell_pri)

            # 평가자산 db에서 조회
            where_condition_eva = [('mod_id', '=', model)]
            eva_asset = select("tot_mod_inv", 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_eva)
            print('평가자산:', eva_asset[0][0])
            # 매도금액/평가자산 퍼센트
            percent_by_eva = total_sell_pri/int(eva_asset[0][0])
            print('매도금액/평가자산 퍼센트:', percent_by_eva)
          
            
            # 모델원금 db에서 select
            where_condition_pri = [('mod_id', '=', model)]
            tot_mod_pri = int(select('tot_mod_pri', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_pri)[0][0])
            print('모델원금:',tot_mod_pri)

            # 매도금액/평가자산 퍼센트를 원금이랑 수익에 곱해주고 그걸 db update
            tot_mod_pri = tot_mod_pri*(1-percent_by_eva)
            print('바뀐 모델원금:', tot_mod_pri)

            # 모델원금 update
            update('mod_act', 'tot_mod_pri', tot_mod_pri, 'mod_id', model)
            print('모델원금 db update완료')
            
            # 모델수익 db에서 select
            where_condition_prf = [('mod_id', '=', model)]
            tot_mod_prf = int(select('tot_mod_prf', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition_prf)[0][0])
            tot_mod_prf = tot_mod_prf*(1-percent_by_eva)
            print('바뀐 모델수익:', tot_mod_prf)
            print('모델수익db에서 select완료')

            # 모델수익 db update
            update('mod_act', 'tot_mod_prf', tot_mod_prf, 'mod_id', model)
            print('모델수익 db update 완료')

            # 모델평가자산 update = tot_mod_pri + tot_mod_prf 
            tot_mod_inv = tot_mod_pri + tot_mod_prf 
            update('mod_act', 'tot_mod_inv', tot_mod_inv, 'mod_id', model)

            # mod_ren_dt 업데이트
            mod_ren_dt = datetime.datetime.today().strftime('%Y-%m-%d')
            update('mod_act', 'mod_ren_dt', 'DATE_FORMAT("'+mod_ren_dt+'","%Y-%m-%d")', 'mod_id', model)
            print('날짜 업데이트 완료')

            # 남은 요청금액은 tb cap_act 출금금액으로 insert
            # 1) 남은 잔고 select해서 잔고금액 확인
            where_condition_balance =  [('mod_id2','=',model)]
            surplus_balance = select('act_bal', 'cap_act', limit=1, offset=None, order_by='id', DESC=True, where_condition=where_condition_balance)
            surplus_balance = int(surplus_balance[0][0])
            
            account = CANO+ACNT_PRDT_CD #계좌번호
            print('남은잔고:', surplus_balance)
            
            # 2) balance에 요청금액 빼기
            surplus_balance -= prc_pri

            # 3) cap_act테이블 insert
            # insert_remain_price(model, account, balance, prc_pri)
            now = datetime.datetime.now()
            values = [(model, account, now, surplus_balance, prc_pri)]
            print('cap_act테이블 인서트할 값:', values)
            insert_many('cap_act', 'mod_id2, cap_act, ren_dt, act_bal, wdr_pri', values)
            print('cap_act insert완료')
            
            # 4) 출금요청 완료하면 trs_check의 prc_cd(처리여부) 1로 update
            result = update('trs_check', 'prc_cd', 1, 'id', index)
            print('trs_check 업데이트결과:',result)
            print('!사용자 출금요청 처리 완료!')
            print('-----------')


def get_stock_data(code):
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()

    #삼성전자 데이터 db daily_price 테이블에서 데이터 가져오기 
    query0="SELECT * FROM daily_price WHERE date BETWEEN '2008-01-01' AND '2023-01-17'AND code={0} ORDER BY date".format(code)
    cur.execute(query0)
    datas = cur.fetchall()
    company = [data for data in datas]
    df = pd.DataFrame(company)
    df = pd.DataFrame(company)
    df.rename(columns = {0:'code', 2:'open', 3:'high', 4:'low', 5:'close', 6:'diff', 7:'volume'}, inplace = True)
    df_date = [df[1][i].strftime('%Y-%m-%d') for i in range(len(datas))]
    df = pd.concat([pd.DataFrame(df_date),df[['code','open','high','low','close','diff','volume']]], axis=1)
    df.rename(columns = {0:'date'}, inplace = True)

    conn.commit()
    # conn.close() close는 언제하는거지 안해도되남

    return df



def get_exchange_rate():
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()
    # db에서 환율 데이터 가져오기
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

    conn.commit()

    return exchange



# db에서 국고채이자율 데이터 가져오기
def get_interest_rate():
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()

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

    return interest


# # DB 일반화
# select 일반화 함수
def select(column_qry:str, table:str, limit=None, offset=None, order_by=None, DESC=None, where_condition:[tuple]=None) -> tuple:
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()

    sql_qr = "SELECT {0} FROM {1}".format(column_qry, table)
    if where_condition:
        for i, (col, eq, val) in enumerate(where_condition):
            is_equal = '=' if eq else '!='
            is_multiple = ' AND' if i > 0 else ' WHERE'
            sql_qr += f'{is_multiple} {col}{is_equal}{val}'

    if order_by:
        sql_qr += ' ORDER BY {}'.format(order_by)
    if DESC:
        sql_qr += ' DESC'
    if limit:
        sql_qr += ' LIMIT {}'.format(limit)
    if offset:
        sql_qr += ' OFFSET {}'.format(offset)
    cur = conn.cursor()
    cur.execute(sql_qr)
    datas = cur.fetchall()

    return datas #tuple로 반환

# insert 일반화 함수
# values는 list 형식으로 넣었음, args로 함
def insert_many(table:str, columns: str, values: list) -> bool:
    print('values:',values)
    print(len(values))
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    sql = f"INSERT INTO {table}({columns}) " \
                "VALUES ("  + ','.join(["%s"]*len(values[0])) + ");"
    try:
        cur = conn.cursor()
        cur.executemany(sql, values)
        conn.commit()
        return True
    except:
        return False

def update(table, set_column, set_value, where_column, where_value) -> bool:
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    sql = '''UPDATE {0} SET {1}={2} WHERE {3}={4};'''.format(table, set_column, set_value, where_column, where_value)
    try:
        cur = conn.cursor()

        cur.execute(sql)
        conn.commit()
        return True
    except:
        return False



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


# 크롤링한 기업리스트
def get_company_list():
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()
    query = "SELECT code FROM company_info "
    cur.execute(query)
    conn.commit()

    company_list=[]
    datas = cur.fetchall()
    for data in datas:
        company_list.append(str(data[0]).zfill(6))

    return company_list


# 기업 지표 계산 결과값
def make_increase_company(company_list):
    print('DB 연결 시작 !')
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')    
    print('DB 접속 성공')
    cur = conn.cursor()
    
    aroon_result={}
    left_com_list = []
    for com in company_list:
        try:
            sql = "SELECT code, high, low FROM daily_price WHERE code={0}".format(com)
            cur.execute(sql)
            results = cur.fetchall()
            print('results 완료')
            company=[res for res in results]
            # print(len(company))
            df = pd.DataFrame(company)
            df.rename(columns = {0:'code', 1:'high', 2:'low'}, inplace = True)
            print('df완료')
            
            if df.isnull().sum().sum() != 0:
                continue
            # print('aroon 시작')
            df['aroondown'], df['aroonup'] = talib.AROON(df['high'], df['low'], timeperiod=14)
            com=df['code'][0]
            # up이 50보다 크고 down이 50보다 작음 : 상승세
            # print('상승세 체크')
            if df['aroondown'][len(df)-1] <= 30:
                if (df['aroonup'][len(df)-1]> 50) & (df['aroondown'][len(df)-1] < 50):
                # 상승세 중에서도 100가까이 가고 30이하에 머물면 추세 발생 확률 높음
                    aroon_result[com] = df['aroonup'][len(df)-1]
                    print(aroon_result)
                    print("aroon_result{0}완료!".format(company_list.index(com)))
        except Exception as e:
            left_com_list.append(com)
            print(left_com_list)
    aroon_result = sorted(aroon_result.items(), key=lambda x: x[1], reverse=True)
    aroon_result = aroon_result[:5]
    aroon_result = [aroon_result[i][0] for i in range(0,len(aroon_result))]
    print(aroon_result)


    print('DB 연결 해제')
    conn.close()

    return aroon_result


# 당일 주문한 기업리스트
def get_daily_order_list(code_list):
    daily_order_list = []
    for code in code_list:
        daily_result = inquire_daily_order(code)
        daily_order_list.append(daily_result)
    return daily_order_list


def make_technical_indicators(df):
    # Directional Movement Index(DMI) : 전일대비 현재가의 고가,중가,저가의 최고값을 이용하여 시장의 방향성과 추세의 강도를 수치로 나타낸 지표/ 추세의 방향 알려주는 추세지표
    df['DMX'] = talib.DX(df['high'], df['low'], df['close'], timeperiod=14)
    # ADX : DMI를 이동평균한 값으로 추세의 강도를 알려주는 지표
    df['ADX'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    df['aroondown'], df['aroonup'] = talib.AROON(df['high'], df['low'], timeperiod=14)
    # ARRONOSC : Aroon Oscillator=AroonUp-AroonDown  (오실레이터=추세의 강도 표시)
    df['ARRONOSC'] = talib.AROONOSC(df['high'], df['low'], timeperiod=14)
    # Balance of power, 
    df['BOP'] = talib.BOP(df['open'], df['high'], df['low'], df['close'])
    # Commodity Channel Index
    df['CCI'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)
    # CMO - Chande Momentum Oscillator
    df['CMO'] = talib.CMO(df['close'], timeperiod=14)
    # MFI - Money Flow Index
    df['MFI'] = talib.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=14)
    # MINUS_DI - Minus Directional Indicator
    df['MINUS_DI'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=14)
    # PLUS_DI - Plus Directional Indicator
    df['PLUS_DI'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=14)
    # PPO - Percentage Price Oscillator
    df['PPO'] = talib.PPO(df['close'], fastperiod=12, slowperiod=26, matype=0)
    # ROC - Rate of change : ((price/prevPrice)-1)*100
    df['ROC'] = talib.ROC(df['close'], timeperiod=10)
    # RSI - Relative Strength Index
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    # STOCH - Stochastic
    df['slowk'], df['slowd'] = talib.STOCH(df['high'], df['low'], df['close'], fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    # STOCHF - Stochastic Fast
    df['fastk'], df['fastd'] = talib.STOCHF(df['high'], df['low'], df['close'], fastk_period=5, fastd_period=3, fastd_matype=0)
    # TRIX - 1-day Rate-Of-Change (ROC) of a Triple Smooth EMA
    df['TRIX'] = talib.TRIX(df['close'], timeperiod=30)
    # ULTOSC - Ultimate Oscillator
    df['ULTOSC'] = talib.ULTOSC(df['high'], df['low'], df['close'], timeperiod1=7, timeperiod2=14, timeperiod3=28)
    # WILLR - Williams' %R
    df['WILLR'] = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=14)

    # df.drop(['high', 'low', 'volume'], axis=1, inplace=True)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df



# 라벨링
# 맨 마지막 값은 그 다음날 종가 정보가 없어서 라벨링이 불가능 -> range(len(df)-1)
def ML_labeling(df):
    df['label']=0

    for i in range(len(df)-1):
        close = df['close'].iloc[i]
        t_close = df['close'].iloc[i+1]

        # 오늘대비 내일 종가 증가율 3퍼 이상이면 buy : 1
        if ((t_close-close)/close)*100 >= 1:
            df['label'].iloc[i]=1
        # sell: 2
        elif ((t_close-close)/close)*100 <= -1:
            df['label'].iloc[i]=2
        # hold : 0

    df['label'].iloc[len(df)-1]=np.NaN # 맨마지막 값은 다음날 종가 정보가 없어서 아직 라벨링 불가능

    return df


def ML_model(code):
    df = get_stock_data(code)
    exchange = get_exchange_rate()
    interest = get_interest_rate()

    merge_df = pd.merge(df, exchange, how='left', on='date')
    merge_df = pd.merge(merge_df, interest, how='left', on='date')

    # 이자율 null값 채우기
    interest_rate_null_list = merge_df.loc[merge_df['interest_rate'].isnull()==True].index.tolist()
    for idx in interest_rate_null_list:
        rate = merge_df['interest_rate'].iloc[idx-1]
        merge_df['interest_rate'].iloc[idx] = rate

    # 환율 null값 채우기
    exchange_rate_null_list = merge_df.loc[merge_df['exchange_rate'].isnull()==True].index.tolist()
    for idx in exchange_rate_null_list:
        rate = merge_df['exchange_rate'].iloc[idx-1]
        merge_df['exchange_rate'].iloc[idx] = rate

    # 기술적 지표 만들기
    df = make_technical_indicators(merge_df)

    # 라벨링
    df = ML_labeling(df)

    # # train, test 분리 - 맨 마지막 값 하나만 예측
    df_train = df.iloc[:-1]
    df_test = pd.DataFrame([df.iloc[-1]])

    X_train, y_train = df_train.iloc[:, 2:-1], df_train.iloc[:, -1]                    
    X_test, y_test = df_test.iloc[:,2:-1], df_test.iloc[:,-1]

    # XGBoost분류모델 생성
    xgb = XGBClassifier(n_estimators = 100, 
                        gamma=0,
                        learning_rate=0.05,
                        max_depth=6,
                        objective= 'multi:softmax')

    # verbose : 학습마다 평가값들에 대한 메세지 출력할지
    xgb.fit(X_train, y_train, verbose=True)
    preds = xgb.predict(X_test)[0]

    # mod_sign 테이블에 insert
    model = '1'
    today = datetime.datetime.today()
    values = [(model, preds, today, code)]
    insert_many('mod_sign', 'mod_id, ord_sig, ord_sig_dt, iem_cd', values)

def ML_calculation():  
    send_message("계산 시작합니다")
    model = '1'
    # 보유주식조회
    print('보유주식조회시작')
    stock_dict = get_stock_balance()
    print('보유주식조회:', stock_dict)
    # 보유한 주식 기업 코드 돌면서 list에 들어감 
    code_list = [code for code in stock_dict.keys()]
    # 장 마감 후 업데이트 해줘야 할 table: 모델거래내역 mod_trs, 모델자산내역 mod_act
    
    # 모델거래내역 mod_trs 업데이트
    try:
        daily_order_list = get_daily_order_list(code_list)
        # 안됨
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

    # 1) mod_act에서 모델id, 업데이트날짜와 수익률 select
    where_condition = [('mod_id', '=', model)]
    values = [select('mod_id, mod_ren_dt, tot_mod_rtr', 'mod_act', limit=None, offset=None, order_by=None, DESC=None, where_condition=where_condition)[0]]
    
    # 2) 모델수익률테이블 mod_prf_info에 수익률 insert
    insert_many('mod_prf_info', 'mod_id, ren_dt, tot_mod_rtr', values)

    # 3) db에서 기업 리스트 가져와서(get_company_list) increase_company 상승세인 기업 선정  
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
    
    # 머신러닝 시그널 생성
    signal_list = []
    if bool(code_list) == False:
        pass
    else:
        for code in code_list:
            ML_model(code)

    send_message('계산 끝났습니다.')


def get_BSH_signal():
    conn = pymysql.connect(host='3.35.49.211', port=3306, user='Team2', password='0120', db='Trading', charset='utf8')
    cur = conn.cursor()
    query = "SELECT * FROM mod_sign WHERE mod_id='1' ORDER BY id DESC LIMIT 5"
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
