def hello():
    return "works!"

def module_test():
    return "✅ 모듈 설치 완료"



import pandas as pd
import numpy as np
import os
import json
from functools import lru_cache

path = '/content/drive/MyDrive/코드잇 3팀 고급 프로젝트/00_원본 csv/'

# 테이블별 전처리 함수
@lru_cache(maxsize=None)
def clean_accounts_user(path=path):
    df = pd.read_csv(
        os.path.join(path, 'accounts_user.csv'),
        usecols=[
            'id',
            'created_at',
            'group_id',
            'gender',
            'ban_status',
            'is_push_on',
            'pending_chat',
            'pending_votes',
            'alarm_count'   # 여기로 옮겨옴
            ]
            )

    # 결측값 삭제
    df = df.dropna(subset=['gender', 'group_id']).copy()

    # 데이터 타입 변경
    df['group_id'] = df['group_id'].astype(int)
    df['created_at'] = pd.to_datetime(df['created_at'])

    # pending chat - 마이너스 값 삭제
    df = df[df['pending_chat'] >= 0].copy()

    # pending chat - 1000 이상인 값을 1000 이하의 최댓값으로 대체
    max_normal = df.loc[df['pending_chat'] <= 1000, 'pending_chat'].max()
    df.loc[df['pending_chat'] > 1000, 'pending_chat'] = max_normal

    # 사용하지 않는 컬럼 삭제
    df = df.drop(columns=['pending_votes'])

    # alarm_count - 238 초과 값을 238로 대체
    df.loc[df['alarm_count'] > 238, 'alarm_count'] = 238

    # 컬럼 순서 변경
    df = df[['id', 'gender', 'is_push_on', 'created_at', 'ban_status', 'pending_chat', 'group_id', 'alarm_count']]

    # 인덱스 초기화
    df = df.reset_index(drop=True)
    
    return df



@lru_cache(maxsize=None)
def clean_accounts_group(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_group.csv'))

    df = df[df['grade'].isin([1, 2, 3])].copy()
    df = df[~df['class_num'].isin([0, 41])].copy()

    users = clean_accounts_user(path=path)

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

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



@lru_cache(maxsize=None)
def clean_accounts_school(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_school.csv'))

    users = clean_accounts_user(path=path)
    groups = clean_accounts_group(path=path)

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

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



@lru_cache(maxsize=None)
def clean_accounts_nearbyschool(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_nearbyschool.csv'))

    users = clean_accounts_user(path=path)
    groups = clean_accounts_group(path=path)
    raw_schools = pd.read_csv(os.path.join(path, 'accounts_school.csv'))

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

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_polls_question(path=path):
    df = pd.read_csv(os.path.join(path, 'polls_question.csv'))

    # 필수 컬럼 기준 결측치 제거
    df = (df
          .dropna(subset=['id', 'question_text', 'created_at'])
          .copy())

    # created_at 컬럼을 datetime 형식으로 변환
    df['created_at'] = pd.to_datetime(df['created_at'])

    # 중복 ID 확인 및 제거
    df = df.drop_duplicates(subset=['id'])

    # created_at 기준 오름차순 정렬 후,
    # 중복된 question_text 중 첫 번째(가장 빨리 만들어진) 데이터만 남기기
    df = df.sort_values(by='created_at', ascending=True)
    df = df.drop_duplicates(subset=['question_text'], keep='first')

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_polls_questionpiece(path=path):
    df = pd.read_csv(os.path.join(path, 'polls_questionpiece.csv'))

    # 필수 컬럼 기준 결측치 제거
    essential_cols = [
        'question_id',
        'is_voted',
        'is_skipped',
        'created_at'
    ]
    df = df.dropna(subset=essential_cols).copy()

    # created_at 컬럼을 datetime 형식으로 변환
    df['created_at'] = pd.to_datetime(df['created_at'])

    # 논리적 이상치 확인: 투표와 스킵이 동시에 1이 된 비정상 데이터 체크
    invalid_rows = ((df['is_voted'] == 1)
                    & (df['is_skipped'] == 1)).sum()

    if invalid_rows > 0:
        df = df[~((df['is_voted'] == 1) & (df['is_skipped'] == 1))]

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_accounts_attendance(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_attendance.csv'))

    attendance_base = df[
        ["id", "user_id", "attendance_date_list"]
    ].copy()

    attendance_base = attendance_base.rename(
        columns={"id": "attendance_record_id"}
    )

    def parse_attendance_date_list(value):
        # 이미 리스트인 경우
        if isinstance(value, list):
            return value, False

        # 결측 또는 빈 문자열
        if pd.isna(value) or str(value).strip() == "":
            return [], False

        try:
            parsed = json.loads(value)

            # 리스트가 아닌 값이 들어온 경우
            if not isinstance(parsed, list):
                return [], True

            return parsed, False

        except (json.JSONDecodeError, TypeError):
            return [], True


    parsed_result = attendance_base[
        "attendance_date_list"
    ].apply(parse_attendance_date_list)

    attendance_base["attendance_dates"] = parsed_result.str[0]
    attendance_base["parse_error"] = parsed_result.str[1]

    attendance_long = (
        attendance_base.loc[
            ~attendance_base["parse_error"],
            [
                "attendance_record_id",
                "user_id",
                "attendance_dates",
            ],
        ]
        .explode(
            "attendance_dates",
            ignore_index=True,
        )
        .rename(
            columns={
                "attendance_dates": "attendance_date"
            }
        )
    )

    attendance_long = attendance_long.dropna(
        subset=["attendance_date"]
    ).copy()

    attendance_long["attendance_date"] = pd.to_datetime(
        attendance_long["attendance_date"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    # 사용자-출석일 단위
    attendance_long_export = attendance_long.copy()

    # 날짜만 저장
    attendance_long_export["attendance_date"] = (
        attendance_long_export["attendance_date"]
        .dt.normalize()
    )
    # 인덱스 초기화
    attendance_long_export = attendance_long_export.reset_index(drop=True)

    return attendance_long_export



def clean_accounts_blockrecord(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_blockrecord.csv'))

    # 날짜형으로 변경
    df["created_at"] = pd.to_datetime(df["created_at"])

    block_raw = df.copy()

    block_raw["reason"] = (
        block_raw["reason"]
        .astype("string")
        .str.strip()
    )

    block_raw = block_raw.sort_values("id").copy()

    # 자기 자신을 차단한 행 삭제
    self_block_mask = (
        block_raw["user_id"]
        .eq(block_raw["block_user_id"])
    )

    block_valid = (
        block_raw.loc[
            ~self_block_mask
            & block_raw["created_at"].notna()
        ]
        .copy()
    )

    # 동일인이 동일인을 같은 시각에 차단한 경우 삭제
    reason_record_keys = [
        "user_id",
        "block_user_id",
        "created_at",
        "reason",
    ]
    block_reason_clean = (
        block_valid
        .sort_values("id")
        .drop_duplicates(
            subset=reason_record_keys,
            keep="first",
        )
        .copy()
    )

    # 동일인이 동일인을 같은 시간에 차단했지만 reason이 다른 경우 하나로 병합
    event_keys = [
        "user_id",
        "block_user_id",
        "created_at",
    ]
    block_event_clean = (
        block_reason_clean
        .sort_values("id")
        .groupby(
            event_keys,
            as_index=False,
            dropna=False,
        )
        .agg(
            # 해당 사건에서 가장 작은 id
            id=("id", "min"),

            # 가장 작은 id 행의 대표 사유
            reason=("reason", "first"),

            # 실제로 기록된 모든 사유
            reason_list=(
                "reason",
                lambda x: tuple(pd.unique(x.dropna())),
            ),

            # 서로 다른 사유 개수
            reason_count=("reason", "nunique"),
        )
    )

    block_event_clean["has_reason_conflict"] = (
        block_event_clean["reason_count"] > 1
    )

    # 동일인이 동일인을 다른 시각에 차단한 경우
    pair_keys = [
        "user_id",
        "block_user_id",
    ]

    block_event_clean = (
        block_event_clean
        .sort_values(
            pair_keys + ["created_at", "id"]
        )
        .reset_index(drop=True)
    )

    # 동일 관계 내 차단 기록 순서
    block_event_clean["block_order_within_pair"] = (
        block_event_clean
        .groupby(pair_keys)
        .cumcount()
        .add(1)
    )

    # 동일 관계의 이전 차단 시각
    block_event_clean["previous_block_at"] = (
        block_event_clean
        .groupby(pair_keys)["created_at"]
        .shift()
    )

    # 이전 차단 기록과의 간격
    block_event_clean["seconds_since_previous_block"] = (
        block_event_clean["created_at"]
        - block_event_clean["previous_block_at"]
    ).dt.total_seconds()

    # 동일 관계에서 두 번째 이상 등장한 기록
    block_event_clean["is_repeated_pair"] = (
        block_event_clean["block_order_within_pair"] > 1
    )

    # 1분 이내 차단이 반복된 행
    block_event_clean["is_rapid_repeat_60s"] = (
        block_event_clean[
            "seconds_since_previous_block"
        ].between(
            0,
            60,
            inclusive="right",
        )
    )

    # 차단 사건 단위
    block_event_export = block_event_clean.copy()

    def collection_to_json(value):
        if isinstance(value, (list, tuple, np.ndarray)):
            converted = [
                item.item()
                if isinstance(item, np.generic)
                else item
                for item in value
            ]

            return json.dumps(
                converted,
                ensure_ascii=False,
            )

        return value

    # 여러 사유가 담긴 튜플을 JSON 문자열로 변환
    block_event_export["reason_list"] = (
        block_event_export["reason_list"]
        .apply(collection_to_json)
    )

    # 인덱스 초기화
    block_event_export = block_event_export.reset_index(drop=True)

    return block_event_export



def clean_polls_questionset(path=path):
    df = pd.read_csv(os.path.join(path, 'polls_questionset.csv'))

    # 전처리용 테이블 생성
    questionset_base = (
        df
        .rename(columns={"id": "questionset_id"})
        .copy()
    )

    # status 값 정리
    questionset_base["status"] = (
        questionset_base["status"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # created_at, opening_time 컬럼 날짜형으로 변환
    for column in ["created_at", "opening_time"]:
        questionset_base[column] = pd.to_datetime(
            questionset_base[column]
        )

    # 문자열을 리스트로 변환
    def parse_question_piece_list(value):
        if isinstance(value, list):
            return value, False

        if pd.isna(value) or str(value).strip() == "":
            return [], False

        try:
            parsed = json.loads(value)

            if not isinstance(parsed, list):
                return [], True

            return parsed, False

        except (json.JSONDecodeError, TypeError):
            return [], True

    parsed_result = (
        questionset_base["question_piece_id_list"]
        .apply(parse_question_piece_list)
    )

    questionset_base["question_piece_ids"] = (
        parsed_result.str[0]
    )

    questionset_base["piece_list_parse_error"] = (
        parsed_result.str[1]
    )

    questionset_base["piece_count"] = (
        questionset_base["question_piece_ids"].str.len()
    )

    # 리스트 구조 체크
    questionset_base["has_duplicate_piece"] = (
        questionset_base["question_piece_ids"]
        .apply(
            lambda values: (
                len(values) != len(set(values))
            )
        )
    )

    questionset_base["has_invalid_piece_type"] = (
        questionset_base["question_piece_ids"]
        .apply(
            lambda values: any(
                not isinstance(value, int)
                for value in values
            )
        )
    )

    # 리스트 튜플화
    questionset_base["question_piece_tuple"] = (
        questionset_base["question_piece_ids"]
        .apply(tuple)
    )

    # created_at, opening_time 비교
    # 차이
    questionset_base["opening_delay_seconds"] = (
        questionset_base["opening_time"]
        - questionset_base["created_at"]
    ).dt.total_seconds()

    # 차이가 0 미만인 경우 이상치
    questionset_base["opening_before_created"] = (
        questionset_base[
            "opening_delay_seconds"
        ] < 0
    )

    # 동일 유저/시점 생성된 질문 세트 - 이상치
    questionset_base["same_user_created_count"] = (
        questionset_base
        .groupby(
            ["user_id", "created_at"]
        )["questionset_id"]
        .transform("size")
    )

    questionset_clean = (
        questionset_base[
            [
                "questionset_id",
                "user_id",
                "status",
                "created_at",
                "opening_time",
                "opening_delay_seconds",
                "opening_before_created",
                "same_user_created_count",
            ]
        ]
        .rename(
            columns={
                "same_user_created_count":
                "same_user_created_at_set_count"
            }
        )
        .copy()
    )

    questionset_export = questionset_clean.copy()

    # 인덱스 초기화
    questionset_export = questionset_export.reset_index(drop=True)

    return questionset_export



def clean_accounts_paymenthistory(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_paymenthistory.csv'))

    # 데이터타입 변경
    # created_at: object -> datetime
    df['created_at'] = pd.to_datetime(df['created_at'])

    # id를 제외한 컬럼 전부에서 중복값일 경우 삭제
    df = (df.drop_duplicates(
        subset=df.columns.difference(['id']),keep='first')
    )

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_accounts_userquestionrecord(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_userquestionrecord.csv'))

    # 데이터타입 변경
    # created_at: object -> datetime
    # answer_updated_at: object -> datetime
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['answer_updated_at'] = pd.to_datetime(df['answer_updated_at'])

    cond = (df['has_read'] == 0) & (df['opened_times'] == 1)
    df = df[~cond].copy()

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_polls_usercandidate(path=path):
    df = pd.read_csv(os.path.join(path, 'polls_usercandidate.csv'))

    # created_at 문자열에서 datetime 타입으로 변환
    df['created_at'] = pd.to_datetime(df['created_at'])

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_accounts_user_contacts(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_user_contacts.csv'))

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_accounts_friendrequest(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_friendrequest.csv'))

    # created_at, updated_at을 문자열에서 datetime 타입으로 변환
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['updated_at'] = pd.to_datetime(df['updated_at'])

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



def clean_accounts_userwithdraw(path=path):
    df = pd.read_csv(os.path.join(path, 'accounts_userwithdraw.csv'))

    # admin/test 사유(테스트/운영 계정 탈퇴)는 분석 대상이 아니므로 제외
    df = df[~df['reason'].isin(['admin', 'test'])].copy()

    # created_at을 문자열에서 datetime 타입으로 변환
    df['created_at'] = pd.to_datetime(df['created_at'])

    # 인덱스 초기화
    df = df.reset_index(drop=True)

    return df



########################################
# 기존 테이블 subset
########################################

@lru_cache(maxsize=None)
def clean_polls_questionset_piece(path=path):
    df = pd.read_csv(os.path.join(path, 'polls_questionset.csv'))

    # 전처리용 테이블 생성
    questionset_base = (
        df
        .rename(columns={"id": "questionset_id"})
        .copy()
    )

    # status 값 정리
    questionset_base["status"] = (
        questionset_base["status"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # created_at, opening_time 컬럼 날짜형으로 변환
    for column in ["created_at", "opening_time"]:
        questionset_base[column] = pd.to_datetime(
            questionset_base[column]
        )

    # 문자열을 리스트로 변환
    def parse_question_piece_list(value):
        if isinstance(value, list):
            return value, False

        if pd.isna(value) or str(value).strip() == "":
            return [], False

        try:
            parsed = json.loads(value)

            if not isinstance(parsed, list):
                return [], True

            return parsed, False

        except (json.JSONDecodeError, TypeError):
            return [], True

    parsed_result = (
        questionset_base["question_piece_id_list"]
        .apply(parse_question_piece_list)
    )

    questionset_base["question_piece_ids"] = (
        parsed_result.str[0]
    )

    questionset_base["piece_list_parse_error"] = (
        parsed_result.str[1]
    )

    questionset_base["piece_count"] = (
        questionset_base["question_piece_ids"].str.len()
    )

    # 리스트 구조 체크
    questionset_base["has_duplicate_piece"] = (
        questionset_base["question_piece_ids"]
        .apply(
            lambda values: (
                len(values) != len(set(values))
            )
        )
    )

    questionset_base["has_invalid_piece_type"] = (
        questionset_base["question_piece_ids"]
        .apply(
            lambda values: any(
                not isinstance(value, int)
                for value in values
            )
        )
    )

    # 리스트 튜플화
    questionset_base["question_piece_tuple"] = (
        questionset_base["question_piece_ids"]
        .apply(tuple)
    )

    # created_at, opening_time 비교
    # 차이
    questionset_base["opening_delay_seconds"] = (
        questionset_base["opening_time"]
        - questionset_base["created_at"]
    ).dt.total_seconds()

    # 차이가 0 미만인 경우 이상치
    questionset_base["opening_before_created"] = (
        questionset_base[
            "opening_delay_seconds"
        ] < 0
    )

    # 동일 유저/시점 생성된 질문 세트 - 이상치
    questionset_base["same_user_created_count"] = (
        questionset_base
        .groupby(
            ["user_id", "created_at"]
        )["questionset_id"]
        .transform("size")
    )

    valid_piece_list_mask = (
        ~questionset_base["piece_list_parse_error"]
        & questionset_base["piece_count"].eq(10)
        & ~questionset_base["has_duplicate_piece"]
        & ~questionset_base["has_invalid_piece_type"]
    )

    questionset_piece_long = (
        questionset_base.loc[
            valid_piece_list_mask,
            [
                "questionset_id",
                "question_piece_ids",
            ],
        ]
        .explode(
            "question_piece_ids",
            ignore_index=True,
        )
        .rename(
            columns={
                "question_piece_ids": "question_piece_id"
            }
        )
    )

    questionset_piece_long["question_piece_id"] = (
        pd.to_numeric(
            questionset_piece_long["question_piece_id"],
            errors="coerce",
        )
        .astype("Int64")
    )

    # 원본 리스트에 저장된 문항 순서
    questionset_piece_long["stored_position"] = (
        questionset_piece_long
        .groupby("questionset_id")
        .cumcount()
        .add(1)
    )

    # 질문 세트-문항 연결 단위
    questionset_piece_export = (
        questionset_piece_long[
            [
                "questionset_id",
                "question_piece_id",
                "stored_position",
            ]
        ]
        .copy()
    )

    # 인덱스 초기화
    questionset_piece_export = questionset_piece_export.reset_index(drop=True)

    return questionset_piece_export