import json
import boto3
import requests
from datetime import datetime, timedelta
import os

# AWS klijent
s3 = boto3.client('s3')
bucket_name = os.environ.get('BUCKET_NAME', 'hn-bronze-300617413048-12345678')  # Ovo ćemo definisati u CloudFormation-u


def get_hackernews_item(item_id):
    """Dohvati jedan item sa Hacker News API-ja"""
    url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Greska pri dohvatanju itema {item_id}: {e}")
    return None


def lambda_handler(event, context):
    print("Pocinjem prikupljanje Hacker News podataka...")

    # Računamo jučerašnji dan (od ponoći do ponoći)
    yesterday = datetime.utcnow() - timedelta(days=1)
    start_timestamp = int(yesterday.replace(hour=0, minute=0, second=0).timestamp())
    end_timestamp = int(yesterday.replace(hour=23, minute=59, second=59).timestamp())

    print(f"Prikupljam podatke za: {yesterday.strftime('%Y-%m-%d')}")
    print(f"Vremenski opseg: {start_timestamp} do {end_timestamp}")

    # Dohvati najnovije priče (max 500)
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        response = requests.get(top_stories_url, timeout=10)
        story_ids = response.json()[:500]  # Uzimamo prvih 500
    except Exception as e:
        print(f"Greska pri dohvatanju top stories: {e}")
        return {'statusCode': 500, 'body': 'Greška pri dohvatanju podataka'}

    print(f"Dohvaćeno {len(story_ids)} story ID-eva")

    # Filtriraj samo one koji su juče kreirani
    collected_items = []
    for idx, item_id in enumerate(story_ids):
        if idx % 50 == 0:
            print(f"Procesiram {idx}/{len(story_ids)}...")

        item = get_hackernews_item(item_id)
        if item and start_timestamp <= item.get('time', 0) <= end_timestamp:
            collected_items.append(item)

    print(f"Pronadjeno {len(collected_items)} itema koji su kreirani juče")

    # Ako nema podataka, ipak kreiraj prazan fajl (da znamo da je pokrenuto)
    if not collected_items:
        collected_items = [{"info": "No data found for this date"}]

    # Kreiraj S3 putanju
    year = yesterday.strftime('%Y')
    month = yesterday.strftime('%m')
    day = yesterday.strftime('%d')
    s3_key = f"bronze/hackernews/year={year}/month={month}/day={day}/hn_{yesterday.strftime('%Y%m%d')}.json"

    # Upisi u S3
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(collected_items, indent=2),
            ContentType='application/json'
        )
        print(f"Uspesno upisano u S3: {s3_key}")
    except Exception as e:
        print(f"Greška pri upisu u S3: {e}")
        return {'statusCode': 500, 'body': f'Greska pri upisu: {e}'}

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Uspesno prikupljeno {len(collected_items)} itema',
            's3_location': f's3://{bucket_name}/{s3_key}',
            'date': yesterday.strftime('%Y-%m-%d')
        })
    }


# Za lokalno testiranje (opciono)
if __name__ == "__main__":
    # Testiranje
    os.environ['BUCKET_NAME'] = 'hn-bronze-300617413048-12345678'
    result = lambda_handler({}, None)
    print(result)