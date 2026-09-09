def hello():
    return "works!"

def module_test():
    return "✅ 모듈 설치 완료"



import pandas as pd
from functools import lru_cache

path = '/content/drive/MyDrive/코드잇 3팀 고급 프로젝트/00_원본 csv/'
clean_path = '/content/drive/MyDrive/코드잇 3팀 고급 프로젝트/01_전처리 완료된 csv'

# 테이블별 전처리 함수
@lru_cache(maxsize=None)
def clean_accounts_user():
    df = pd.read_csv(
        path + 'accounts_user.csv',
        usecols=[
            'id',
            'created_at',
            'group_id',
            'gender',
            'ban_status',
            'is_push_on',
            'pending_chat',
            'pending_votes'
            ]
            )

    # 결측값 삭제
    df = df.dropna(subset=['gender', 'group_id']).copy()

    # 데이터 타입 변경
    df['group_id'] = df['group_id'].astype(int)

    # pending chat - 마이너스 값 삭제
    df = df[df['pending_chat'] >= 0].copy()

    # pending chat - 1000 이상인 값을 1000 이하의 최댓값으로 대체
    max_normal = df.loc[df['pending_chat'] <= 1000, 'pending_chat'].max()
    df.loc[df['pending_chat'] > 1000, 'pending_chat'] = max_normal

    # 사용하지 않는 컬럼 삭제
    df = df.drop(columns=['pending_votes'])

    # alarm 컬럼 추가
    alarm = pd.read_csv(
        path + 'accounts_user.csv',
        usecols=['id', 'alarm_count']
    )
    df = df.merge(
        alarm,
        on='id',
        how='left',
        validate='one_to_one'
    )

    # alarm_count - 238 초과 값을 238로 대체
    df.loc[df['alarm_count'] > 238, 'alarm_count'] = 238

    return df



@lru_cache(maxsize=None)
def clean_accounts_group():
    df = pd.read_csv(path + 'accounts_group.csv')

    df = df[df['grade'].isin([1, 2, 3])].copy()
    df = df[~df['class_num'].isin([0, 41])].copy()

    users = clean_accounts_user()

    group_users = (
        users
        .groupby('group_id')
        .size()
        .reset_index(name='user_count')
        )
    
    class20_check = (
        df[df['class_num'] == 20]
        .merge(
            group_users,
            left_on='id',
            right_on='group_id',
            how='left'
        )
    )

    class20_zero = class20_check[class20_check['user_count'].isna()]
    df = df[~df['id'].isin(class20_zero['id'])].copy()

    return df



@lru_cache(maxsize=None)
def clean_accounts_school():
    df = pd.read_csv(path + 'accounts_school.csv')

    users = clean_accounts_user()
    groups = clean_accounts_group()

    user_school = (
        users[['id', 'group_id']]
        .merge(
            groups[['id', 'school_id']],
            left_on='group_id',
            right_on='id',
            how='left',
            suffixes=('_user', '_group')
        )
    )

    school_user_count = (
        user_school.groupby('school_id')['id_user']
        .nunique()
        .reset_index(name='actual_user_count')
    )

    schools_check = df.merge(
        school_user_count,
        left_on='id',
        right_on='school_id',
        how='left'
    )

    schools_check['actual_user_count'] = schools_check['actual_user_count'].fillna(0)

    # student_count=0 이고 실제 유저도 0명인 학교만 삭제
    delete_ids = schools_check.loc[
        (schools_check['student_count'] == 0) &
        (schools_check['actual_user_count'] == 0),
        'id'
    ]

    df = df[~df['id'].isin(delete_ids)].copy()

    return df



@lru_cache(maxsize=None)
def clean_accounts_nearbyschool():
    df = pd.read_csv(path + 'accounts_nearbyschool.csv')

    users = clean_accounts_user()
    groups = clean_accounts_group()
    raw_schools = pd.read_csv(path + 'accounts_school.csv')

    df = df[
        ~df['school_id'].isin([5948, 5949]) &
        ~df['nearby_school_id'].isin([5948, 5949])
    ].copy()

    user_school = (
        users[['id', 'group_id']]
        .merge(
            groups[['id', 'school_id']],
            left_on='group_id',
            right_on='id',
            how='left',
            suffixes=('_user', '_group')
        )
    )

    school_user_count = (
        user_school.groupby('school_id')['id_user']
        .nunique()
        .reset_index(name='actual_user_count')
    )
    
    schools_check = raw_schools.merge(
        school_user_count,
        left_on='id',
        right_on='school_id',
        how='left'
    )
    schools_check['actual_user_count'] = schools_check['actual_user_count'].fillna(0)

    delete_ids = schools_check.loc[
        (schools_check['student_count'] == 0) &
        (schools_check['actual_user_count'] == 0),
        'id'
    ]

    df = df[
        ~df['school_id'].isin(delete_ids) &
        ~df['nearby_school_id'].isin(delete_ids)
    ].copy()

    df = df[
        df['school_id'] != df['nearby_school_id']
    ].copy()

    return df



def clean_polls_question():
    df = pd.read_csv(path + 'polls_question.csv')

    df = (df
          .dropna(subset=['id', 'question_text', 'created_at'])
          .copy())

    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.drop_duplicates(subset=['id'])

    df = df.sort_values(by='created_at', ascending=True)
    df = df.drop_duplicates(subset=['question_text'], keep='first')

    return df