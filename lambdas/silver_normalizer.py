import awswrangler as wr
import json
import boto3
import pandas as pd
from datetime import datetime, timedelta
import re
import html
import os
import requests


s3 = boto3.client('s3')
BUCKET = os.environ.get('BUCKET_NAME', 'hn-bronze-300617413048-12345678')

# Jučerašnji dan
yesterday = datetime.utcnow() - timedelta(days=1)
year = yesterday.strftime('%Y')
month = yesterday.strftime('%m')
day = yesterday.strftime('%d')


def clean_html(text):
    if not text:
        return ""

    #text = text.encode().decode('unicode_escape')       # 1. Dekodiraj Unicode escape sekvence (\u003C → <)
    text = html.unescape(text)        # 2. Dekodiraj HTML entitete (&#x2F; → /, &lt; → <)
    text = re.sub(r'<[^>]+>', '', text)        # 3. Ukloni HTML tagove (<a href=...>)
    text = re.sub(r'\s+', ' ', text)        # 4. Ukloni višestruke razmake i novi red

    return text.strip()


def convert_time(timestamp):
    return datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'


def get_user_karma(username):
    url = f'https://hacker-news.firebaseio.com/v0/user/{username}.json'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('karma', 0)
    except Exception as e:
        print(f'Greska za username {username}: {e}')
    return 0


def get_post_type(tags):
    if not tags:
        return 'story'

    priority = ['job', 'poll', 'comment', 'ask_hn', 'show_hn', 'story']
    for tag in priority:
        if tag in tags:
            return tag

    return 'story'


def extract_post_and_user(item, platform, i):
    username = item.get('author')

    if platform == 'Hacker News':
        karma_score = get_user_karma(username) if (i % 100 == 0) else 5.0
        post_type = get_post_type(item.get('_tags', []))
        text = clean_html(item.get(f'{post_type}_text', ''))
        is_verified = None
        followers = None
        points = item.get('points')
    else:  # TWITTER
        karma_score = None
        post_type = 'tweet'
        text = item.get('tweet_text')
        is_verified = item.get('verified')
        followers = item.get('followers')
        points = None

    post = {
        'post_id': item.get('objectID'),
        'author': username,
        'type': post_type,
        'text': text,
        'platform': platform,
        'points': points,
        'created_at': item.get('created_at'),
        'date': yesterday.strftime('%Y-%m-%d')
    }
    user = {
        'user_id': username,
        'username': username,
        'platform': platform,
        'karma_score': karma_score,
        'is_verified': is_verified,
        'followers': followers,
        'date': yesterday.strftime('%Y-%m-%d')
    }

    return post, user


def create_parquet(data_list, id_column, filename):
    df = pd.DataFrame(data_list)
    df = df.drop_duplicates(subset=[id_column])
    users_file = filename
    df.to_parquet(users_file, index=False)
    return df


def lambda_handler(event, context):
    print("Počinjem normalizaciju...")

    prefix = "bronze"
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)

    if 'Contents' not in response:
        return {'statusCode': 404, 'body': 'No data'}

    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    latest_files = [files[0]['Key'], files[1]['Key']]

    users_list = []
    posts_list = []

    for file in latest_files:
        obj = s3.get_object(Bucket=BUCKET, Key=file)
        data = json.loads(obj['Body'].read())

        i = 0
        platform = 'Hacker News' if 'hackernews' in file else 'X'
        for item in data:
            post, user = extract_post_and_user(item, platform, i)
            users_list.append(user)
            posts_list.append(post)

            i += 1


    df_users = create_parquet(users_list, id_column='user_id', filename='users.parquet')
    df_posts = create_parquet(posts_list, id_column='post_id', filename='posts.parquet')

    s3_key = "silver/.../"
    s3_posts_key = f"silver/posts"
    s3_users_key = f"silver/users"


    wr.s3.to_parquet(
        df=df_posts,
        path="s3://hn-bronze-300617413048-12345678/" + s3_posts_key,
        dataset=True,
        partition_cols=['date']
    )

    wr.s3.to_parquet(
        df=df_users,
        path="s3://hn-bronze-300617413048-12345678/" + s3_users_key,
        dataset=True,
        partition_cols=['platform', 'date']
    )

    return {
        'statusCode': 200,
        'body': json.dumps({'count': len(df_posts), 'location': s3_key})
    }


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(result)
