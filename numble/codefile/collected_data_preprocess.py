import pandas as pd
import re


# 행정구역 컬럼 함수
def address_area(series):
    address_category = []
    for address in series:
        area = address[:2]
        address_category.append(area)

    return address_category

# 기업입지 조건 함수 (구와 읍에 있을 경우 도심(1), 아니면 비도심(0))
def city_condition(series):
    pattern = '\w+구'
    pattern2 = '\w+읍'

    city_category = []
    for address in series:
        result = re.findall(pattern, address)
        result2 = re.findall(pattern2, address)
        if result or result2:
            city_category.append(1)
        else:
            city_category.append(0)

    return city_category



def nice_data_prepare(nice_active_df, nice_inactive_df):

    # 주소 결측치 대체 - 출처) BIZ_NO 홈페이지 사업자번호 검색
    nice_active_df['address'].loc[nice_active_df['address'].isnull()] = '경상북도 김천시 어모면 옥계리 산103'
    nice_active_df['address'].loc[nice_active_df.BIZ_NO==3128100483] = '충청남도 아산시 선장면 신성리산 113-8'

    # 행정구역 두 글자로 통일
    address_chg = {'서울':['서울특별시'], '부산':['부산광역시'], '대구':['대구광역시'], '인천':['인천광역시'], '광주':['광주광역시'], '대전':['대전광역시'], '울산':['울산광역시'],
    '경기':['경기도'], '강원':['강원도'], '충북':['충청북도'], '충남':['충청남도'], '전북':['전라북도'], '전남':['전라남도'], '경북':['경상북도'], '경남':['경상남도'], 
    '제주':['제주특별자치도', '제주도'], '세종':['세종특별자치시']}

    change_address_map = {word:k for k, v in address_chg.items() for word in v}

    nice_active_df['address'] = nice_active_df.address.replace(change_address_map, regex=True)
    nice_inactive_df['address'] = nice_inactive_df.address.replace(change_address_map, regex=True)

    nice_active_df['행정구역'] = address_area(nice_active_df['address'])
    nice_inactive_df['행정구역'] = address_area(nice_inactive_df['address'])

    #기업입지 컬럼 만들기
    nice_active_df['기업입지'] = city_condition(nice_active_df['address'])
    nice_inactive_df['기업입지'] = city_condition(nice_inactive_df['address'])

    # 필요한 컬럼만 선택
    select_columns_ex = ['BIZ_NO', 'grade', '행정구역', '기업입지']

    nice_active_df = nice_active_df[select_columns_ex]
    nice_inactive_df = nice_inactive_df[select_columns_ex]

    # 컬럼명 변경
    for df in [nice_active_df, nice_inactive_df]:
        df.columns = ['사업자번호', '산업등급','행정구역', '기업입지']

    return nice_active_df, nice_inactive_df


# 결합하고 처리하는 함수
def nice_combine(df_active_left, df_inactive_left, nice_active_df, nice_inactive_df):
    
    # 외부데이터 결합
    df_active = pd.merge(df_active_left, nice_active_df, left_on='사업자번호', right_on='사업자번호', how='outer')
    df_inactive = pd.merge(df_inactive_left, nice_inactive_df, left_on='사업자번호', right_on='사업자번호', how='outer')

    # 결측치 대체
    # grade - mean값으로 결측치 대체
    df_active.산업등급.fillna(round(df_active['산업등급'].mean(), 2), inplace=True)
    df_inactive.산업등급.fillna(round(df_inactive['산업등급'].mean(), 2), inplace=True)

    # city - mean으로 결측치 대체
    df_active.기업입지.fillna(round(df_active['기업입지'].mean(),2), inplace=True)
    df_inactive.기업입지.fillna(round(df_inactive['기업입지'].mean(),2), inplace=True)

    # 행정구역 - 주소없음으로 결측치 대체
    df_active.행정구역.fillna('주소없음', inplace=True)
    df_inactive.행정구역.fillna('주소없음', inplace=True)

    return df_active, df_inactive


def incruit_prepare(incruit_company):
    incruit_result = []
    pattern = r"\([^)]*\)"

    for company in incruit_company:
        company = re.sub(pattern = pattern, repl = "", string = company)
        company = company.replace(" ", "")
        company = company.replace("자)", "")
        company = company.replace("주)", "")
        company = company.replace("㈜", "")
        company = company.replace("주식회사", "")
        company = company.replace("유한회사", "")
        company = company.replace(".", "")
        company = company.replace("kuti", "")
        company = company.replace("elimdmp", "엘림디엠피")
        company = company.replace("thecompany", "더컴퍼니")
        company = company.replace("ITSENG", "아이티에스엔지니어링")
        company = company.replace("DUTKOREA", "디유티코리아")
        company = company.replace("SPSYSTEMS", "에스피시스템스")
        company = company.replace("TS-TECH", "티에스테크")
        company = company.replace("HELLOMYNAMEIS", "헬로우마이네임이즈")
        company = company.replace("NKEC", "엔케이이씨")
        company = company.replace("HY", "에이치와이")
        company = company.replace("cijkorea", "씨아이제이코리아")
        company = company.replace("JCBIO", "제이씨바이오")
        company = company.replace("GTCTechnologyKoreaLtd", "슐저지티씨테크놀로지코리아")
        company = company.strip()
        incruit_result.append(company)

    return incruit_result

def find_incruit_company(incruit_result, df_active, df_inactive):

    active_company_list = df_active["기업명"].unique().tolist()
    inactive_company_list = df_inactive["기업명"].unique().tolist()
    company_name_list = active_company_list+inactive_company_list

    find_result = []

    for company in incruit_result:
        if company in company_name_list:
            find_result.append(company)

    df_active['우수기업']=0
    df_inactive['우수기업']=0

    
    for idx, company in enumerate(df_active['기업명']):
        if company in incruit_result:
            df_active['우수기업'].iloc[idx]=1
        else:
            continue

    for idx, company in enumerate(df_inactive['기업명']):
        if company in incruit_result:
            df_inactive['우수기업'].iloc[idx]=1
        else:
            continue