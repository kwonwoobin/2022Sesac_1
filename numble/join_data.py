import pandas as pd


active_df = pd.merge(df_active_join, df_nice_active, left_on='BIZ_NO', right_on='BIZ_NO', how='outer')
inactive_df = pd.merge(df_inactive_join, df_nice_inactive, left_on='BIZ_NO', right_on='BIZ_NO', how='outer')

# 필요없는 피처 drop
active_df = active_df.drop(['BIZ_NO', 'CMP_NM', 'CEO_NM'], axis=1)
inactive_df = inactive_df.drop(['BIZ_NO', 'CMP_NM', 'CEO_NM'], axis=1)

# grade - mean값으로 결측치 대체
active_df.grade.fillna(round(active_df['grade'].mean(), 2), inplace=True)
inactive_df.grade.fillna(round(inactive_df['grade'].mean(), 2), inplace=True)

# city - mean으로 결측치 대체
active_df.city.fillna(round(active_df['city'].mean(),2), inplace=True)
inactive_df.city.fillna(round(active_df['city'].mean(),2), inplace=True)

# 액티브와 휴폐업 데이터프레임 합치기
df_join = pd.merge(active_df, inactive_df, how='outer')