# numble data 전처리 함수들 
from sklearn.preprocessing  import LabelEncoder
import pandas as pd


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

    #국가 null값 한국으로 채우기
    df.NATN_NM.fillna('한국', inplace=True)
     
    # 'EMP_CNT' 직원수 구간화
    df.EMP_CNT.fillna(-1, inplace=True)
    df['EMP_CAT']=df['EMP_CNT'].apply(lambda x : get_category(x))


    return df
    



def numble_preprocess(active_df, inactive_df, active_record_df, inactive_record_df):

    # 기업명 컬럼명 변경
    active_df = active_df.rename(columns={'CMP_NM1':'CMP_NM'})
    
    #사용할 컬럼들
    select_columns = ['BIZ_NO','CMP_NM', 'BZ_TYP',  'HDOF_BR_GB', 'FR_IVST_CORP_YN', 'VENT_YN', 'LIST_CD', 'MDSCO_PRTC_YN','NATN_NM', 'ESTB_DATE', 'ESTB_GB', 'EMP_CNT']
    active_df = active_df.loc[:, select_columns]
    inactive_df = inactive_df.loc[:, select_columns]

    #이상치 처리 - 직원수가 16310명인 회사 BIZ_NO 6038138153 광평건설 직원수 22로 바꾸기(출처:bizno)
    inactive_df['EMP_CNT'].iloc[204]=22

    # 전처리 함수 feature engineering 적용
    active_df = feature_engineering(active_df)
    inactive_df = feature_engineering(inactive_df)

    # 직원수 컬럼 drop
    active_df = active_df.drop('EMP_CNT', axis=1)
    inactive_df = inactive_df.drop('EMP_CNT', axis=1)

    # 컬럼명 한글로 변경
    for df in [active_df, inactive_df]:
        df.columns=['사업자번호', '기업명', '업종', '본점지점구분', '국외투자법인여부', '벤처기업여부', '상장여부', '중견기업보호여부', '국가', '설립구분', '설립날짜', '직원수']

    # 휴폐업이력 sheet를 기준으로 휴폐업이력 컬럼 추가
    # 상태 - 부도(1), 휴업(2), 폐업(3)만 가져오는 조건
    condition = (active_record_df['CLSBZ_GB']==1) | (active_record_df['CLSBZ_GB']==2) | (active_record_df['CLSBZ_GB']==3)
    active_record_Y = active_record_df.loc[condition]
    condition2 = (inactive_record_df['CLSBZ_GB']==1) | (inactive_record_df['CLSBZ_GB']==2) | (inactive_record_df['CLSBZ_GB']==3)
    inactive_record_Y = inactive_record_df.loc[condition2]

    # 중복행 제거
    active_record_Y = active_record_Y.drop_duplicates(['BIZ_NO'])
    inactive_record_Y = inactive_record_Y.drop_duplicates(['BIZ_NO'])
    active_record_Y['휴폐업이력'] = 1
    inactive_record_Y['휴폐업이력'] = 1

    # 컬럼명 한글로 변경
    for df in [active_record_Y, inactive_record_Y]:
        df.columns = ['사업자번호', '상태종료일자', '데이터입수일자', '상태', '휴폐업발생일자', '휴폐업이력']

    # 데이터프레임 left join
    df_active_left = pd.merge(active_df, active_record_Y, left_on = '사업자번호', right_on='사업자번호', how='left')
    df_inactive_left = pd.merge(inactive_df, inactive_record_Y, left_on = '사업자번호', right_on='사업자번호', how='left')

    # 필요없는 피처 drop
    df_active_left = df_active_left.drop(['상태','데이터입수일자','상태종료일자'], axis=1)
    df_inactive_left = df_inactive_left.drop(['상태','데이터입수일자','상태종료일자'], axis=1)

    # 결측치 대체
    df_active_left.휴폐업이력.fillna(0, inplace=True)
    df_active_left.휴폐업발생일자.fillna(99999999, inplace=True)

    return df_active_left, df_inactive_left


# 인코딩 함수
def label_encoding(df):

    #레이블 인코딩
    label_encode_features = ['업종', '국외투자법인여부', '벤처기업여부', '중견기업보호여부', '국가', '행정구역']

    for feature in label_encode_features:
        le = LabelEncoder()
        le = le.fit(df[feature])
        df[feature] = le.transform(df[feature])
        

    # 업력 라벨링
    estb_mapping = {"1970년 이전":0, "1970년대":1, "1980년대":2, "1990년대":3, "2000년대 전기":4, "2000년대 후기":5, "2010년대 전기":6, "2010년대 후기":7, "2020년대 전기":8, "해당 없음":9 }
    df['설립날짜'] = df['설립날짜'].map(estb_mapping)

    # 직원수 라벨링
    emp_mapping = {'NaN&zero':0, '1~10':1, '10~50':2, '50~300':3, '300~':4}
    df['직원수'] = df['직원수'].map(emp_mapping)

    return df