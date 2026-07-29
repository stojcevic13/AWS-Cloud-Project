import json
import boto3
import pandas as pd
from datetime import datetime
import re
import os

s3 = boto3.client('s3')
BUCKET = os.environ.get('BUCKET_NAME', 'hn-bronze-300617413048-12345678')


def clean_html(text):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def convert_time(timestamp):
    return datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'


def lambda_handler(event, context):
    print("Počinjem normalizaciju...")

    prefix = "bronze/hackernews/"
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)

    if 'Contents' not in response:
        return {'statusCode': 404, 'body': 'No data'}

    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    latest_file = files[0]['Key']

    obj = s3.get_object(Bucket=BUCKET, Key=latest_file)
    data = json.loads(obj['Body'].read())

    rows = []
    for item in data:
        if not item or 'id' not in item:
            continue

        rows.append({
            'post_id': str(item.get('id')),
            'author': item.get('by', 'unknown'),
            'text': clean_html(item.get('text', '')),
            'title': item.get('title', ''),
            'score': item.get('score', 0),
            'created_at': convert_time(item.get('time', 0)),
            'type': item.get('type', 'unknown'),
            'url': item.get('url', '')
        })

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=['post_id'])

    output_file = 'posts.parquet'
    df.to_parquet(output_file, index=False)

    year = datetime.utcnow().year
    month = datetime.utcnow().month
    day = datetime.utcnow().day

    s3_key = f"silver/posts/year={year}/month={month}/day={day}/posts.parquet"
    s3.upload_file(output_file, BUCKET, s3_key)

    return {
        'statusCode': 200,
        'body': json.dumps({'count': len(df), 'location': s3_key})
    }


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(result)