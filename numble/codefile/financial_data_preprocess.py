import numpy as np
import pandas as pd
import math

# 연도만 가져오는 함수

def DATE4word(series):

    # 결과 값을 담을 리스트 year_category 초기화
    year_category = []

    # for 반복문을 통해 판다스 시리즈 내의 각 날짜를 순회
    for date in series:

        # 날짜의 0번째 인덱스부터 3번째 인덱스까지 슬라이싱하여 정수형(Integer)으로 변환 후 변수 year에 할당
        year = str(date)[0 : 4]
        year_category.append(year)

    # 결과 값 반환
    return year_category


# 액티브(휴폐업이력 有)  사용할 재무데이터만 남기는 함수
def delete_semi_active(df):
    semi_del_list=[]

    for i in range(len(df)):
        if df.iloc[i]['휴폐업발생일자']!=99999999:

            fiscal_year = int(df.iloc[i]['결산연도'])
            inactive_year = int(str(df.iloc[i]['휴폐업발생일자'])[:4])

            # 결산년이 휴폐업발생년도보다 작은 경우와 휴폐업발생년도 1,2년전 데이터만 남기기
            if (fiscal_year < inactive_year) :
                if (fiscal_year == inactive_year-1) or (fiscal_year == inactive_year-2):
                    pass
                else:
                    semi_del_list.append(i)
            else:
                semi_del_list.append(i)

        # 휴폐업 발생이력 없는 경우 데이터 삭제
        else:
            semi_del_list.append(i)
    
    # 데이터 삭제
    df = df.drop(df.index[semi_del_list], axis=0)

    # 인덱스 reset
    df.reset_index(drop=True, inplace=True)

    return df



# 액티브 기업(휴폐업이력無) 사용할 재무데이터만 남기는 함수
def delete_normal_active(df):

    normal_del_list=[]

    for i in range(len(df)):

        fiscal_year = int(df.iloc[i]['결산연도'])

        # 결산년도 2020, 2021년만 남기고 삭제
        if fiscal_year == 2021 or fiscal_year == 2020:
            pass
        else:
            normal_del_list.append(i)

    # 데이터 삭제
    df = df.drop(df.index[normal_del_list], axis=0)

    # 인덱스 reset
    df.reset_index(drop=True, inplace=True)

    return df



# 휴폐업 기업  사용할 재무데이터만 남기는 함수
def delete_inactive(df):

    inactive_del_list=[]

    for i in range(len(df)):

        fiscal_year = int(df.iloc[i]['결산연도'])
        inactive_year = int(str(df.iloc[i]['휴폐업발생일자'])[:4])

        # 휴폐업발생년도 기준 1,2년전 데이터만 남기고 삭제
        if fiscal_year == inactive_year-1 or fiscal_year == inactive_year-2:
            pass
        else:
            inactive_del_list.append(i)

    df = df.drop(df.index[inactive_del_list], axis=0)
    df.reset_index(drop=True, inplace=True)

    return df


# 반기, 분기 재무데이터 통합하여 연도 데이터로 만들어주는 함수
def make_financial_yeardata(financial_df):
    
    # 결산년월을 연도로 바꿔주기
    financial_df['결산연도'] = DATE4word(financial_df['결산년월'])

    # 결산년도 컬럼 drop
    financial_df.drop('결산년월', axis=1, inplace=True)

    # 2022년 데이터 drop
    del_year_row = []
    for i, data in enumerate(financial_df['결산연도']):
        if str(data)[:4]=='2022':
            del_year_row.append(i)

    financial_df = financial_df.drop(financial_df.index[del_year_row], axis=0)
    financial_df.reset_index(drop=True, inplace=True)

    # 반기, 분기 데이터 결합해서 연도 데이터로 만들기
    sum_columns = ['사업자번호', '결산연도','유동자산',  '매출채권',  '비유동자산', '유형자산', '자산총계', '유동부채',  '비유동부채', '부  채  총  계', '자본금', '이익잉여금(결손금）',
    '자본총계', '매출액', '판매비와관리비', '영업이익（손실）',  '법인세비용차감전순손익', '법인세비용', '당기순이익(손실)',  '미수금', '매출원가', '무형자산', '재고자산' ]
    mean_columns = ['사업자번호',  '결산연도','기업순이익률(%)', '유보액/총자산(%)',  '유보액/납입자본(%)', '매출액총이익률(%)', '매출액영업이익률(%)', '매출액순이익률(%)', '수지비율(%)', '경상수지비율', '영업비율(%)', '금융비용대매출액비율(%', '금융비용대부채비율(%)', '금융비용대총비용비율(%', '부채비율(%)',
    '차입금의존도(%)', '자기자본비율(%)', '순운전자본비율(%)', '유동부채비율(%)', '비유동부채비율(%)', '부채총계대 매출액(%)', '총자본회전율(회)', '재고자산회전율(회)', '매출채권회전율(회)', '매입채무회전율(회)']

    sum_financial_df = financial_df[sum_columns]
    mean_financial_df = financial_df[mean_columns]

    sum_financial_df = sum_financial_df.groupby(['사업자번호', '결산연도']).sum()
    mean_financial_df = mean_financial_df.groupby(['사업자번호', '결산연도']).mean()

    # 인덱스 reset
    sum_financial_df = sum_financial_df.reset_index()
    mean_financial_df = mean_financial_df.reset_index()

    # 재무데이터 다시 결합
    financial_df = pd.concat([sum_financial_df, mean_financial_df], axis=1)

    # 중복 컬럼 삭제
    financial_df = financial_df.loc[:, ~financial_df.T.duplicated()]

    return financial_df


def make_financial_column(financial_df):

    # 재무데이터 df의 기업 unique list
    financial_company_list = financial_df['사업자번호'].unique().tolist()

    # groupby해서 재무데이터 2개 있는 기업, 1개 있는 기업 list 뽑기
    groupby_financial = financial_df.groupby(['사업자번호', '결산연도']).sum()

    # 재무데이터 1개년 있는 회사 리스트
    onedata_list=[]
    for company in financial_company_list:
        if len(groupby_financial.loc[company]) == 1 :
            onedata_list.append(company)

    # 재무데이터 2개년 있는 회사 리스트
    twodata_list=[]
    for company in financial_company_list:
        if len(groupby_financial.loc[company]) == 2 :
            twodata_list.append(company)

    # 추가 컬럼 생성
    financial_df['총자본순이익률'] = (financial_df['당기순이익(손실)']/financial_df['자본총계'])*100
    financial_df['이자비용'] = (financial_df['기업순이익률(%)']*financial_df['자산총계']) - financial_df['당기순이익(손실)']
    financial_df['이자보상비율'] =(financial_df['영업이익（손실）']/financial_df['이자비용'] )*100
    financial_df['금융비용부담률(%)'] = (financial_df['매출액']/financial_df['이자비용'])*100

    # 증가율 컬럼 
    # 1) 비율df랑 숫자df 먼저 분리

    percent_feature = ['사업자번호', '결산연도', '휴폐업발생일자', '휴폐업이력', '기업순이익률(%)', '유보액/총자산(%)', '유보액/납입자본(%)', '매출액총이익률(%)', '매출액영업이익률(%)', 
    '매출액순이익률(%)', '수지비율(%)', '경상수지비율', '영업비율(%)', '금융비용대매출액비율(%', '금융비용대부채비율(%)', '금융비용대총비용비율(%', '부채비율(%)', '차입금의존도(%)', '자기자본비율(%)', 
    '순운전자본비율(%)', '유동부채비율(%)', '비유동부채비율(%)', '부채총계대 매출액(%)', '총자본회전율(회)', '재고자산회전율(회)', '매출채권회전율(회)',
    '매입채무회전율(회)',  '총자본순이익률',   '이자보상비율', '금융비용부담률(%)']

    number_feature = ['사업자번호',
    '결산연도',  '휴폐업발생일자', '유동자산', '매출채권',   '비유동자산', '유형자산', '자산총계', '유동부채', '비유동부채', '부  채  총  계',
    '자본금', '이익잉여금(결손금）', '자본총계', '매출액', '판매비와관리비', '영업이익（손실）', '법인세비용차감전순손익', '법인세비용', 
    '당기순이익(손실)', '미수금',
    '매출원가', '무형자산', '재고자산', '이자비용']

    # 증가율 컬럼과 숫자 컬럼 구분해서 따로 데이터프레임 생성
    percent_financial_df = financial_df[percent_feature]
    number_financial_df = financial_df[number_feature]

    # 숫자 컬럼에서 기업별로 데이터1개/2개 구분
    onedata_company_num_df = number_financial_df[number_financial_df.groupby("사업자번호")["결산연도"].transform("size") == 1]
    onedata_company_num_df.reset_index(drop=True, inplace=True)
    twodata_company_num_df = number_financial_df[number_financial_df.groupby("사업자번호")["결산연도"].transform("size") > 1]
    twodata_company_num_df.reset_index(drop=True, inplace=True)

    # 데이터 하나인 기업은 증가율 컬럼 모두 0
    onedata_company_num_df['매출액증가율(%)']=0
    onedata_company_num_df['순이익증가율(%)']=0

    # 데이터 2개인 기업, 매출액 하나라도 0이면 매출액증가율 0
    revenue_zero_df = twodata_company_num_df[['사업자번호', '결산연도', '매출액']].loc[twodata_company_num_df['매출액']==0]
    revenue_zero_df['매출액증가율(%)'] = 0
    revenue_zero_df.drop(['결산연도', '매출액'], axis=1, inplace=True)
    revenue_zero_df.drop_duplicates(inplace=True)

    revenue_growthrate_df=pd.DataFrame(((twodata_company_num_df.groupby('사업자번호').max()['매출액'] - twodata_company_num_df.groupby('사업자번호').min()['매출액'] ) / twodata_company_num_df.groupby('사업자번호').min()['매출액'] )*100)

    revenue_growthrate_df.columns = ['매출액증가율(%)']
    revenue_growthrate_df.reset_index(inplace=True)


    # for문 돌려서 revenue_zero_df의 기업 돌리면서 매출액증가율 0으로 바꾸기
    revenue_zero_company = revenue_zero_df.사업자번호.tolist()

    for i in range(len(revenue_growthrate_df)):
        if revenue_growthrate_df.iloc[i]['사업자번호'] in revenue_zero_company:
            revenue_growthrate_df['매출액증가율(%)'].iloc[i]=0

    # twodata_company_num_df 에 구한 매출액증가율 revenue_growthrate_df merge
    twodata_company_num_df = pd.merge(twodata_company_num_df,revenue_growthrate_df, left_on='사업자번호', right_on='사업자번호', how='left' )


    # 데이터 2개인 기업, '당기순이익(손실)' 하나라도 0이면 매출액증가율 0 (총523개)
    profit_zero_df = twodata_company_num_df[['사업자번호', '결산연도', '당기순이익(손실)']].loc[twodata_company_num_df['당기순이익(손실)']==0]

    profit_zero_df['순이익증가율(%)'] = 0

    profit_zero_df.drop(['결산연도', '당기순이익(손실)'], axis=1, inplace=True)
    profit_zero_df.drop_duplicates(inplace=True)

    profit_growthrate_df=pd.DataFrame(((twodata_company_num_df.groupby('사업자번호').max()['당기순이익(손실)'] - twodata_company_num_df.groupby('사업자번호').min()['당기순이익(손실)'] ) / twodata_company_num_df.groupby('사업자번호').min()['당기순이익(손실)'] )*100)

    profit_growthrate_df.columns = ['순이익증가율(%)']
    profit_growthrate_df.reset_index(inplace=True)

    # for문 돌려서 revenue_zero_df의 기업 돌리면서 매출액증가율 0으로 바꾸기

    profit_zero_company = profit_zero_df.사업자번호.tolist()

    for i in range(len(profit_growthrate_df)):
        if profit_growthrate_df.iloc[i]['사업자번호'] in profit_zero_company:
            profit_growthrate_df['순이익증가율(%)'].iloc[i]=0

    # twodata_company_num_df 에 구한 매출액증가율 revenue_growthrate_df merge
    twodata_company_num_df = pd.merge(twodata_company_num_df, profit_growthrate_df, left_on='사업자번호', right_on='사업자번호', how='left' )

    # 다시 concat
    growth_rate_df = pd.concat([onedata_company_num_df, twodata_company_num_df])[['사업자번호','매출액증가율(%)', '순이익증가율(%)']]

    # 중복 row 제거
    growth_rate_df.drop_duplicates(inplace=True)

    preprocessed_financial_df = pd.merge(percent_financial_df, growth_rate_df, left_on='사업자번호', right_on='사업자번호', how='left')

    fin_df1 = preprocessed_financial_df.loc[preprocessed_financial_df['휴폐업발생일자']!=99999999]
    fin_df2 = preprocessed_financial_df.loc[preprocessed_financial_df['휴폐업발생일자']==99999999]

    # 휴폐업발생일자 99999999 삭제 - drop옵션으로 기준은 사업자번호로 잡고 최근 연도만 남기기
    fin_df2 = fin_df2.drop_duplicates(['사업자번호'], keep='last')

    # 휴폐업발생일자 있는 경우 : 휴폐업연도의 1년전 데이터만 남기기
    fin_del_list=[]

    for i in range(len(fin_df1)):
        if int(fin_df1.iloc[i]['결산연도']) == int(str(fin_df1.iloc[i]['휴폐업발생일자'])[:4])-1 :
            pass
        else:
            fin_del_list.append(i)

    fin_df1 = fin_df1.drop(fin_df1.index[fin_del_list], axis=0)

    preprocessed_financial_df = pd.concat([fin_df1, fin_df2])
    preprocessed_financial_df.reset_index(drop=True, inplace=True)

    

    return preprocessed_financial_df



# 열에 대하여 이상치 여부를 판별해주는 함수
def is_outlier(df, column, dict_q3, dict_q1, dict_iqr):

    q3 = dict_q3[column]
    q1 = dict_q1[column]
    iqr = dict_iqr[column]

    number = df[column]

    # 이상치 판별
    if number > q3 + 1.5 * iqr or number < q1 - 1.5 * iqr:
        return np.NaN
    else:
        return number


def replace_outlier(preprocessed_financial_df):

    fin_column_list = preprocessed_financial_df.columns.tolist()
    fin_column_list = fin_column_list[4:]

    # 1) 1조 값을 널값으로 대체
    preprocessed_financial_df = preprocessed_financial_df.replace(1000000000000.00, np.NaN)

    # 2) 100000보다 큰 값 이상치로 보고 널값으로 대체 
    for col in fin_column_list:
        column_category = []
        for i, num in enumerate(preprocessed_financial_df[col]):
            if math.isnan(num):
                column_category.append(np.NaN)
            # 1억보다 클 때도 널값으로 대체
            elif num > 100000.00:
                column_category.append(np.NaN)
            else:
                column_category.append(num)

        preprocessed_financial_df[col] = column_category

    # apply 함수를 통하여 각 값의 이상치 여부를 찾고 새로운 열에 결과 저장


    return preprocessed_financial_df