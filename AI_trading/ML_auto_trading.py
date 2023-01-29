
import datetime
import time
from pandas.io.stata import relativedelta
# import pytz

from AI_module import get_access_token, send_message, get_stock_balance, get_balance, get_current_price, buy, sell, process_user_withdrawal
from AI_module import update_users, ML_calculation, get_BSH_signal



try:
    ACCESS_TOKEN = get_access_token()
    send_message("===국내 주식 자동매매 프로그램을 시작합니다===")

    model = '1'
    # KST = pytz.timezone('Asia/Seoul')
    t_now = datetime.datetime.now()
    t_9 = t_now.replace(hour=9, minute=0, second=0, microsecond=0)
    t_exit = t_now.replace(hour=15, minute=00, second=0,microsecond=0)
    t_close_buy_exit = t_now.replace(hour=15, minute=30, second=0, microsecond=0)
    today = datetime.date.today()
    today_day = today.weekday()
    t_calculate_start = t_now.replace(hour=18, minute=0, second=0, microsecond=0)
    t_calculate_end = t_calculate_start + relativedelta(hours = 4)

    # 토요일이나 일요일이면 그 다음 월요일 자정이 되면 break
    if today_day != 5 or today_day != 6:

        # cron 장외 시간 계산: pm 6시
        if t_calculate_start < t_now < t_calculate_end:
            send_message('ML 계산 시작')
            ML_calculation()
            print('ML_calculation 끝')
            update_users()
            print('update_users 끝')
            send_message('ML 계산 끝')
            

        # 사용자 요청시 9시에 전날 종가 매도(cron:9시)
        # AM 09:00 - 장 끝나는 시간
        elif t_9 < t_now < t_exit:
            send_message('사용자출금요청 확인 후 매도')
            process_user_withdrawal(model)

            # 바로 매수 시작
            send_message('매수시작!')
            stock_dict = get_stock_balance() # 보유 주식 조회(딕셔너리)
            present_balance = get_balance() # api잔고조회
            present_balance = present_balance-(present_balance*0.25)
            send_message('남은 잔고 가져오기 완료!')

            buy_signal_list, sell_signal_list, hold_signal_list = get_BSH_signal()
            print('buy_signal_list:', buy_signal_list)
            print('sell_signal_list:', sell_signal_list)
            print('hold_signal_list:', hold_signal_list)
            send_message('signal 가져오기!')
            if len(buy_signal_list) != 0:
                target_buy_count = len(buy_signal_list) #매수할 종목 수
                buy_percent = round(1/target_buy_count, 3) # 종목당 매수 금액 비율
                buy_amount = present_balance*buy_percent  # 종목별 주문 금액 계산
                print('종목별가능주문금액:', buy_amount)
            
            # 보유주식없고 매수신호 없는 경우
            if stock_dict == False and buy_signal_list==[]:
                send_message('보유주식없고 매수신호 없는 경우 pass')
                pass
            # 사용자 요청시 8시 40분에 전날 종가 매도
            # 8시에 DB에 업데이트된 사용자 요청 처리
            else:
                # 잔고 부족하면 프로그램 종료
                for code in buy_signal_list:
                    current_price = get_current_price(code) # 해당 주식 현재가 조회
                    print('종목:',code,'현재가:',current_price)
                    if present_balance < current_price:
                        send_message('잔고부족으로 종료')
                        break
                    buy_qty = 0  # 매수할 수량 초기화
                    buy_qty = int(buy_amount // current_price)
                    print('종목별 주문수량:', buy_qty, '주문종목:', code)
                    result = buy(code, buy_qty)
                    send_message('매수완료')
                    time.sleep(1)
                    # 잔고, 보유수량 업데이트할 필요 없음 - api로 조회                   
            pass

        # 3:15 - PM 3:30 : 신호 매도면 종가가격으로 매도(cron 오후 3시)
        elif t_exit < t_now < t_close_buy_exit:
            send_message('매도 시작합니다.')
            stock_dict = get_stock_balance()
            print('현재보유주식:', stock_dict)
            buy_signal_list, sell_signal_list, hold_signal_list = get_BSH_signal()
            # print('BSH시그널리스트:', buy_signal_list, sell_signal_list, hold_signal_list)

            for code in sell_signal_list:
                print('sell_signal_list안에 들어옴')
                print('매도할 주식코드', code)
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
