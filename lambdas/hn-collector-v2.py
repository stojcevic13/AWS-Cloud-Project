import json
import boto3
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import os

s3 = boto3.client('s3')
BUCKET = os.environ.get('BUCKET_NAME', 'hn-bronze-300617413048-12345678')


def fetch_items_by_tag(tag, start_ts, end_ts, max_hits=1000):
    """Dohvata objave za dati tag (story, ask_hn, job, poll) preko HN Search API"""
    base_url = "https://hn.algolia.com/api/v1/search"

    params = {
        "tags": tag,
        "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
        "hitsPerPage": max_hits
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"Tražim: {tag}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read())
            hits = data.get('hits', [])
            print(f"  Pronađeno {len(hits)} {tag}")
            return hits
    except Exception as e:
        print(f"Greška pri dohvatanju {tag}: {e}")
        return []


def fetch_comments_for_day(start_ts, end_ts, max_hits=1000):
    """Dohvata SVE komentare za određeni dan preko HN Search API"""
    base_url = "https://hn.algolia.com/api/v1/search"

    params = {
        "tags": "comment",
        "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
        "hitsPerPage": max_hits
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print("Tražim komentare...")

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = json.loads(response.read())
            hits = data.get('hits', [])
            print(f"  Pronađeno {len(hits)} komentara")
            return hits
    except Exception as e:
        print(f"Greška pri dohvatanju komentara: {e}")
        return []


def lambda_handler(event, context):
    print("Počinjem prikupljanje Hacker News podataka...")

    # Jučerašnji dan
    yesterday = datetime.utcnow() - timedelta(days=1)
    start_ts = int(yesterday.replace(hour=0, minute=0, second=0).timestamp())
    end_ts = int(yesterday.replace(hour=23, minute=59, second=59).timestamp())

    print(f"Prikupljam podatke za: {yesterday.strftime('%Y-%m-%d')}")

    # 1. Prikupi sve objave (story, ask, job, poll)
    all_posts = []
    for tag in ["story", "ask_hn", "job", "poll"]:
        posts = fetch_items_by_tag(tag, start_ts, end_ts)
        all_posts.extend(posts)

    print(f"Ukupno objava: {len(all_posts)}")

    # 2. Prikupi SVE komentare za taj dan (JEDAN zahtev!)
    all_comments = fetch_comments_for_day(start_ts, end_ts)

    print(f"Ukupno komentara: {len(all_comments)}")

    # 3. Upisi u S3
    year = yesterday.strftime('%Y')
    month = yesterday.strftime('%m')
    day = yesterday.strftime('%d')
    date_str = yesterday.strftime('%Y%m%d')

    # Objave
    posts_key = f"bronze/hackernews/posts/year={year}/month={month}/day={day}/posts_{date_str}.json"
    s3.put_object(
        Bucket=BUCKET,
        Key=posts_key,
        Body=json.dumps(all_posts, indent=2),
        ContentType='application/json'
    )
    print(f"✅ Upisane objave: {posts_key}")

    # Komentari
    if all_comments:
        comments_key = f"bronze/hackernews/comments/year={year}/month={month}/day={day}/comments_{date_str}.json"
        s3.put_object(
            Bucket=BUCKET,
            Key=comments_key,
            Body=json.dumps(all_comments, indent=2),
            ContentType='application/json'
        )
        print(f"✅ Upisani komentari: {comments_key}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'date': yesterday.strftime('%Y-%m-%d'),
            'posts': len(all_posts),
            'comments': len(all_comments)
        })
    }

if __name__ == "__main__":
    # Testiranje
    os.environ['BUCKET_NAME'] = 'hn-bronze-300617413048-12345678'
    result = lambda_handler({}, None)
    print(result)