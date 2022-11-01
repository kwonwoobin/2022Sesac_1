
import pandas as pd
import numpy as np

df_active = pd.read_excel("./data/1_Active_MS_Business_Info.xlsx", sheet_name = 0)
df_active_record = pd.read_excel("./data/1_Active_MS_Business_Info.xlsx", sheet_name = 2)
df_inactive = pd.read_excel("./data/2_Inactive_MS_Business_Info.xlsx", sheet_name = 0)
df_inactive_record = pd.read_excel("./data/2_Inactive_MS_Business_Info.xlsx", sheet_name = 1)

# 기업명 컬럼명 변경
df_active = df_active.rename(columns={'CMP_NM1':'CMP_NM'})

#사용할 컬럼들
select_columns = ['BIZ_NO','CMP_NM', 'CEO_NM', 'BZ_TYP',  'HDOF_BR_GB', 'FR_IVST_CORP_YN', 'VENT_YN', 'LIST_CD', 'MDSCO_PRTC_YN', 'ESTB_DATE', 'ESTB_GB', 'EMP_CNT']


df_active_select = df_active.loc[:, select_columns]
df_inactive_select = df_inactive.loc[:, select_columns]




# 업력 구간화 함수
def estb_date_calc(series):

    # 결과 값을 담을 리스트 year_category 초기화
    year_category = []

    # for 반복문을 통해 판다스 시리즈 내의 각 날짜를 순회
    for date in series:

        # 날짜의 0번째 인덱스부터 3번째 인덱스까지 슬라이싱하여 정수형(Integer)으로 변환 후 변수 year에 할당
        year = int(date[0 : 4])

        # 각 설립연도의 조건에 따라 범주화
        if year < 1970: year_category.append("1970년 이전")
        elif year < 1980: year_category.append("1970년대")
        elif year < 1990: year_category.append("1980년대")
        elif year < 2000: year_category.append("1990년대")
        elif year < 2005: year_category.append("2000년대 전기")
        elif year < 2010: year_category.append("2000년대 후기")
        elif year < 2015: year_category.append("2010년대 전기")
        elif year < 2020: year_category.append("2010년대 후기")
        elif year < 2025: year_category.append("2020년대 전기")
        else: year_category.append("해당 없음")

    # 결과 값 반환
    return year_category


# 직원수 구간화
def get_category(EMP_CNT):
    EMP_CAT = ''
    if EMP_CNT == 0 and -1: EMP_CAT = 'NaN&zero'
    elif EMP_CNT <= 10: EMP_CAT = '1~10'
    elif EMP_CNT <= 50: EMP_CAT = '10~50'
    elif EMP_CNT <= 300: EMP_CAT = '50~300'
    elif EMP_CNT > 300: EMP_CAT = '300~'
    return EMP_CAT


# 데이터 전처리 함수
def feature_engineering(df):

    # 대표자명
    df['CEO_NM'] = df['CEO_NM'].str.replace("외\s*[0-9]+명", "")


    #'LIST_CD' 상장여부로 0, 1
    df.LIST_CD.fillna(0, inplace=True)
    df['LIST_CD'].loc[df['LIST_CD']!=0]=1

    
    # 'ESTB_DATE' 설립날짜 -> 업력 구간화
    df.ESTB_DATE.fillna(99999999, inplace=True)
    # 열의 값을 str으로 변경
    df["ESTB_DATE"] = df["ESTB_DATE"].astype(str)
    # estb_date_calc() 함수를 실행한 결과를 "ESTB_DATE_CAT" 열을 새로 만들어 기존 데이터프레임에 추가
    df["ESTB_DATE_CAT"] = estb_date_calc(df["ESTB_DATE"])
    
    # 필요없는 컬럼 drop
    df = df.drop('ESTB_DATE', axis=1)
     
    # 'EMP_CNT' 직원수 구간화
    df.EMP_CNT.fillna(-1, inplace=True)
    df['EMP_CAT']=df['EMP_CNT'].apply(lambda x : get_category(x))


    return df
    


#이상치 처리 - BIZ_NO 6038138153 광평건설 직원수 16310-> 22로 바꾸기(출처:bizno)
df_inactive_select['EMP_CNT'].iloc[204]=22

# feature engineering 함수 적용
df_active_select = feature_engineering(df_active_select)
df_inactive_select = feature_engineering(df_inactive_select)

# 직원수 컬럼 drop
df_inactive_select = df_inactive_select.drop('EMP_CNT', axis=1)
df_active_select = df_active_select.drop('EMP_CNT', axis=1)

# CEO_NM 결측치(active 1개, inactive 1개) - 'NaN'으로 대체
df_active_select['CEO_NM'].fillna('NaN', inplace=True)
df_inactive_select['CEO_NM'].fillna('NaN', inplace=True)


# 휴폐업이력 sheet에서 휴폐업이력 유무(close_y_n), 휴폐업횟수(close_count) 컬럼 만들기
def close_record(df):

    df.STAT_OCR_DATE.fillna(99999999, inplace=True)
    
    #close_y_n : 휴폐업 유무 컬럼
    df['close_y_n']=1

    #BIZ_NO로 set인덱스
    df=df.set_index('BIZ_NO')

    #휴폐업 조건으로 필터링한 새로운 컬럼 - 휴폐업이력 있는 기업만 들어있는 df 만들기
    close_condition = (df.CLSBZ_GB==1) | (df.CLSBZ_GB==2) | (df.CLSBZ_GB==3)
    condition_df_record = df[close_condition]

    #휴폐업 횟수 구하기
    condition_df_record = condition_df_record.groupby('BIZ_NO').sum()

    # 휴폐업 횟수 컬럼 추가
    df['close_count'] = condition_df_record['close_y_n']

    #index reset
    df = df.reset_index()

    #중복인덱스 삭제하기 - 열지정하여 중복제거
    df= df.drop_duplicates(['BIZ_NO']).reset_index(drop=True)

    return df


df_active_record = close_record(df_active_record)
df_inactive_record = close_record(df_inactive_record)
df_active_record.close_count.fillna(0, inplace=True)



df_active_innerjoin = pd.merge(df_active_select, df_active_record, left_on='BIZ_NO',right_on='BIZ_NO', how='inner')
df_active_innerjoin = df_active_innerjoin[['BIZ_NO', 'close_y_n', 'close_count']]

df_inactive_innerjoin = pd.merge(df_inactive_select, df_inactive_record,left_on='BIZ_NO',right_on='BIZ_NO', how='inner')
df_inactive_innerjoin = df_inactive_innerjoin[['BIZ_NO', 'close_y_n', 'close_count']]

# 데이터프레임 결합
df_active_join = pd.merge(df_active_select, df_active_innerjoin ,left_on='BIZ_NO',right_on='BIZ_NO', how='outer')
df_inactive_join = pd.merge(df_inactive_select, df_inactive_innerjoin ,left_on='BIZ_NO',right_on='BIZ_NO', how='outer')

# 널값 채우기
df_active_join = df_active_join.fillna(0)

# type 변경
df_active_join[['close_y_n', 'close_count']] = df_active_join[['close_y_n', 'close_count']].astype('int')
