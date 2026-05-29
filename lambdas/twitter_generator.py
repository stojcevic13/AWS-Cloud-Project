import json
import random
from datetime import datetime, timedelta
import os

# Tvoj S3 bucket
BUCKET_NAME = "hn-bronze-300617413048-12345678"

# Lista mogućih korisnika
USERS = [
    {"user": "cloud_engineer", "followers": 1250, "verified": False},
    {"user": "crypto_trader", "followers": 5800, "verified": True},
    {"user": "data_scientist", "followers": 3400, "verified": False},
    {"user": "tech_blogger", "followers": 2100, "verified": True},
    {"user": "dev_journey", "followers": 890, "verified": False},
    {"user": "aws_expert", "followers": 4500, "verified": True},
    {"user": "python_lover", "followers": 1200, "verified": False},
    {"user": "security_analyst", "followers": 3100, "verified": True}
]

# Lista mogućih tekstova
TEXTS = [
    "Just deployed my first serverless app on AWS! #cloud",
    "Learning about Medallion architecture today",
    "Hacker News is my favorite source of tech news",
    "Working on my cloud computing project",
    "AWS Lambda vs EC2 - which one do you prefer?",
    "Data engineering is fascinating",
    "Just discovered a new Python library for data processing",
    "Serverless is the future of cloud computing",
    "My S3 bucket is filling up with data!",
    "CloudFormation makes infrastructure so much easier"
]


def generate_tweets():
    """Generiše lažne tweetove za jučerašnji dan"""
    yesterday = datetime.now() - timedelta(days=1)
    num_tweets = random.randint(5, 15)
    tweets = []

    for i in range(num_tweets):
        user_data = random.choice(USERS)
        tweet = {
            "id": f"{int(yesterday.timestamp())}_{i}",
            "text": random.choice(TEXTS),
            "user": user_data["user"],
            "followers_count": user_data["followers"],
            "verified": user_data["verified"],
            "created_at": yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        tweets.append(tweet)

    return tweets, yesterday


def save_local(tweets, date):
    """Sačuva tweetove u lokalni JSON fajl"""
    filename = f"../twitter_data/tweets_{date.strftime('%Y%m%d')}.json"
    with open(filename, 'w') as f:
        json.dump(tweets, f, indent=2)
    print(f" Sačuvano lokalno: {filename}")
    return filename


def upload_to_s3(tweets, date):
    """Upload-uje tweetove u S3 bucket"""
    import boto3

    s3 = boto3.client('s3')
    s3_key = f"bronze/twitter/year={date.year}/month={date.month:02d}/day={date.day:02d}/tweets_{date.strftime('%Y%m%d')}.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(tweets, indent=2),
        ContentType='application/json'
    )
    print(f" Upload-ovano u S3: {s3_key}")
    return s3_key


if __name__ == "__main__":
    print("=" * 50)
    print("TWITTER GENERATOR - Lokalno generisanje lažnih tweetova")
    print("=" * 50)

    #  Generiši tweetove
    print("\n Generišem tweetove...")
    tweets, date = generate_tweets()
    print(f"   Generisano {len(tweets)} tweetova za {date.strftime('%Y-%m-%d')}")

    #  Sačuvaj lokalno
    print("\n Čuvanje...")
    local_file = save_local(tweets, date)
    upload_to_s3(tweets, date)

    print("\n Gotovo!")