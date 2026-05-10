import requests
import os
import re
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 설정
engine = create_engine("sqlite:///youtube_trend.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True)
    title = Column(String)
    channel = Column(String)
    thumbnail = Column(String)
    published_at = Column(String)
    views = Column(Integer)
    likes = Column(Integer)
    comments = Column(Integer)
    score = Column(Float)
    url = Column(String)
    category_id = Column(String)
    category_name = Column(String)
    is_shorts = Column(Integer)  # 0: 롱폼, 1: 쇼츠
    updated_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

CATEGORIES = {
    "1":  "영화/애니메이션",
    "2":  "자동차",
    "10": "음악",
    "15": "동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "20": "게임",
    "22": "사람/블로그",
    "23": "코미디",
    "24": "엔터테인먼트",
    "25": "뉴스/정치",
    "26": "노하우/스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "비영리/사회운동",
}

# search.list로 보충할 카테고리
SEARCH_CATEGORIES = {
    "1":  "영화/애니메이션",
    "2":  "자동차",
    "15": "동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "23": "코미디",
    "24": "엔터테인먼트",
    "27": "교육",
    "29": "비영리/사회운동",
}

def parse_duration_seconds(duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def check_shorts(video):
    duration = video["contentDetails"]["duration"]
    seconds = parse_duration_seconds(duration)

    title = video["snippet"].get("title", "").lower()
    description = video["snippet"].get("description", "").lower()
    tags = [t.lower() for t in video["snippet"].get("tags", [])]

    shorts_keywords = ["#shorts", "#short", "#쇼츠", "#shortvideo", "#shortsvideo"]
    has_shorts_tag = (
        any(kw in title for kw in shorts_keywords) or
        any(kw in description for kw in shorts_keywords) or
        any("short" in t for t in tags)
    )

    if has_shorts_tag:
        return True

    return seconds <= 120

def custom_score(views, likes, comments, published_at):
    published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    age_hours = max((datetime.now(timezone.utc) - published_dt).total_seconds() / 3600, 1)
    engagement = (likes + comments) / max(views, 1)

    return (
        views * 0.3 +
        likes * 5.0 +
        comments * 8.0 +
        engagement * 100000 +
        (1 / age_hours) * 50000
    )

def fetch_and_save():
    print(f"[{datetime.now()}] 데이터 수집 시작...")
    session = Session()

    try:
        # 기존 데이터 삭제
        session.execute(text("DELETE FROM videos"))

        all_shorts = []
        seen_shorts = set()

        for category_id, category_name in CATEGORIES.items():
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,statistics,contentDetails",
                "chart": "mostPopular",
                "regionCode": "KR",
                "videoCategoryId": category_id,
                "maxResults": 50,
                "key": API_KEY
            }
            response = requests.get(url, params=params)
            videos = response.json().get("items", [])

            longform = []

            for v in videos:
                stats = v["statistics"]
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                published_at = v["snippet"]["publishedAt"]
                score = custom_score(views, likes, comments, published_at)
                shorts = check_shorts(v)

                if shorts:
                    if v["id"] not in seen_shorts:
                        seen_shorts.add(v["id"])
                        all_shorts.append((v, score))
                else:
                    longform.append((v, score))

            print(f"[{category_name}] 롱폼: {len(longform)}개 / 쇼츠: {len([v for v in videos if check_shorts(v)])}개")
            # 롱폼 상위 10개 저장
            if len(longform) < 3:
                continue

            longform_sorted = sorted(longform, key=lambda x: x[1], reverse=True)[:10]

            for v, score in longform_sorted:
                session.merge(Video(
                    id=v["id"],
                    title=v["snippet"]["title"],
                    channel=v["snippet"]["channelTitle"],
                    thumbnail=v["snippet"]["thumbnails"]["high"]["url"],
                    published_at=v["snippet"]["publishedAt"],
                    views=int(v["statistics"].get("viewCount", 0)),
                    likes=int(v["statistics"].get("likeCount", 0)),
                    comments=int(v["statistics"].get("commentCount", 0)),
                    score=score,
                    url=f"https://www.youtube.com/watch?v={v['id']}",
                    category_id=category_id,
                    category_name=category_name,
                    is_shorts=0,
                    updated_at=datetime.now()
                ))

        
        # 쇼츠 상위 20개 저장
        shorts_sorted = sorted(all_shorts, key=lambda x: x[1], reverse=True)[:20]
        for v, score in shorts_sorted:
            session.merge(Video(
                id=v["id"],
                title=v["snippet"]["title"],
                channel=v["snippet"]["channelTitle"],
                thumbnail=v["snippet"]["thumbnails"]["high"]["url"],
                published_at=v["snippet"]["publishedAt"],
                views=int(v["statistics"].get("viewCount", 0)),
                likes=int(v["statistics"].get("likeCount", 0)),
                comments=int(v["statistics"].get("commentCount", 0)),
                score=score,
                url=f"https://www.youtube.com/shorts/{v['id']}",
                category_id="shorts",
                category_name="쇼츠 TOP 20",
                is_shorts=1,
                updated_at=datetime.now()
            ))

        session.commit()
        print(f"[{datetime.now()}] 데이터 수집 완료")

    except Exception as e:
        print(f"[{datetime.now()}] 오류: {e}")
        session.rollback()
    finally:
        session.close()

def search_and_supplement():
    print(f"[{datetime.now()}] search.list 보충 시작...")
    session = Session()

    try:
        for category_id, category_name in SEARCH_CATEGORIES.items():
            # 현재 해당 카테고리 롱폼 영상 수 확인
            count = session.query(Video).filter(
                Video.category_id == category_id,
                Video.is_shorts == 0
            ).count()

            # 10개 이상이면 보충 불필요
            if count >= 10:
                continue

            needed = 10 - count
            print(f"[{category_name}] {needed}개 보충 필요")

            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "type": "video",
                "videoCategoryId": category_id,
                "regionCode": "KR",
                "relevanceLanguage": "ko",
                "order": "viewCount",
                "videoDuration": "medium",  # 4분~20분 (롱폼)
                "maxResults": 20,
                "key": API_KEY
            }
            response = requests.get(url, params=params)
            items = response.json().get("items", [])

            if not items:
                continue

            # video ID 목록으로 상세 정보 조회
            video_ids = [item["id"]["videoId"] for item in items]
            detail_url = "https://www.googleapis.com/youtube/v3/videos"
            detail_params = {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": API_KEY
            }
            detail_response = requests.get(detail_url, params=detail_params)
            videos = detail_response.json().get("items", [])

            # 롱폼만 필터링 후 점수 계산
            longform = [v for v in videos if not check_shorts(v)]
            scored = []
            for v in longform:
                stats = v["statistics"]
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                published_at = v["snippet"]["publishedAt"]
                score = custom_score(views, likes, comments, published_at)
                scored.append((v, score))

            scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)[:needed]

            for v, score in scored_sorted:
                # 이미 있는 영상은 건너뜀
                exists = session.query(Video).filter(Video.id == v["id"]).first()
                if exists:
                    continue

                session.add(Video(
                    id=v["id"],
                    title=v["snippet"]["title"],
                    channel=v["snippet"]["channelTitle"],
                    thumbnail=v["snippet"]["thumbnails"]["high"]["url"],
                    published_at=v["snippet"]["publishedAt"],
                    views=int(v["statistics"].get("viewCount", 0)),
                    likes=int(v["statistics"].get("likeCount", 0)),
                    comments=int(v["statistics"].get("commentCount", 0)),
                    score=score,
                    url=f"https://www.youtube.com/watch?v={v['id']}",
                    category_id=category_id,
                    category_name=category_name,
                    is_shorts=0,
                    updated_at=datetime.now()
                ))

        session.commit()
        print(f"[{datetime.now()}] search.list 보충 완료")

    except Exception as e:
        print(f"[{datetime.now()}] 보충 오류: {e}")
        session.rollback()
    finally:
        session.close()

@app.get("/api/trending")
def get_trending():
    session = Session()
    try:
        # 마지막 업데이트 시각
        latest = session.query(Video).order_by(Video.updated_at.desc()).first()
        updated_at = latest.updated_at.strftime("%Y-%m-%d %H:%M") if latest else None

        result = []

        for category_id, category_name in CATEGORIES.items():
            videos = (
                session.query(Video)
                .filter(Video.category_id == category_id)
                .order_by(Video.score.desc())
                .all()
            )
            if not videos:
                continue

            result.append({
                "categoryId": category_id,
                "categoryName": category_name,
                "videos": [
                    {
                        "id": v.id,
                        "title": v.title,
                        "channel": v.channel,
                        "thumbnail": v.thumbnail,
                        "publishedAt": v.published_at,
                        "views": v.views,
                        "likes": v.likes,
                        "comments": v.comments,
                        "score": v.score,
                        "url": v.url,
                    }
                    for v in videos
                ],
            })

        # 쇼츠
        shorts = (
            session.query(Video)
            .filter(Video.category_id == "shorts")
            .order_by(Video.score.desc())
            .all()
        )
        if shorts:
            result.append({
                "categoryId": "shorts",
                "categoryName": "쇼츠 TOP 20",
                "videos": [
                    {
                        "id": v.id,
                        "title": v.title,
                        "channel": v.channel,
                        "thumbnail": v.thumbnail,
                        "publishedAt": v.published_at,
                        "views": v.views,
                        "likes": v.likes,
                        "comments": v.comments,
                        "score": v.score,
                        "url": v.url,
                    }
                    for v in shorts
                ],
            })

        return {"updatedAt": updated_at, "categories": result}

    finally:
        session.close()

# 서버 시작 시 즉시 수집 + 1시간마다 자동 수집
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_save, "interval", hours=1, next_run_time=datetime.now())
scheduler.add_job(search_and_supplement, "interval", hours=6, next_run_time=datetime.now())
scheduler.start()