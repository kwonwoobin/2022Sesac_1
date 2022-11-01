import pandas as pd

df_nice_active = pd.read_excel("./외부data/act_company_information.xls", sheet_name = 0)
df_nice_inactive = pd.read_excel("./외부data/rest_company_information.xls", sheet_name = 0)

df_nice_active.address.fillna('NaN', inplace=True)

# 기업입지(도시,비도시) 기준
city_df = pd.read_excel("./외부data/용도지역(시군구)-비도시지역_2021.xlsx", sheet_name = 0, index_col=[0,1,2])

city_df.reset_index(drop=False, inplace=True)
city_df = pd.DataFrame(city_df.iloc[4:, :3])
city_df.columns=['시', '군,구', '2021']
city_df.drop(city_df.loc[city_df['군,구']=='소계'].index, inplace=True)
city_df['city'] = 0
city_df = city_df.reset_index()
city_df.drop('index', inplace=True, axis=1)

city_condition = city_df['2021']==0
city_df['city'].loc[city_condition]=1


# 데이터프레임에 도심(city) 컬럼 추가
df_nice_active['city'] = 0
df_nice_inactive['city'] = 0

city_index = city_df.loc[city_df['city']==1].index
city_list = city_df['군,구'][city_index].to_list()

for df in [df_nice_active, df_nice_inactive] :
    for city in city_list:
        city_condition = df['address'].str.contains(city)
        df['city'].loc[city_condition]=1

# 필요한 컬럼만 선택
select_columns_ex = ['BIZ_NO', 'grade', 'city']

df_nice_active = df_nice_active[select_columns_ex]
df_nice_inactive = df_nice_inactive[select_columns_ex]

