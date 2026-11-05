
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
import re

# YOUR NEWS INTERESTS
SEARCHES = {
    "Wildlife & Conservation":
        "wildlife conservation success species recovery habitat restoration",

    "Science & Medicine":
        "scientific discovery medical breakthrough research treatment",

    "Archaeology & Anthropology":
        "archaeology discovery ancient civilization anthropology",

    "Economics & Statistics":
        "economic improvement poverty reduction employment progress data",

    "Technology & Inventions":
        "new invention technological breakthrough innovation",

    "Environment & Climate Solutions":
        "environmental improvement clean energy conservation restoration",

    "Politics & Public Policy":
        "successful public policy bipartisan cooperation government reform"
}

# Only a small share of searches are political.
MAX_ARTICLES = 60
MAX_AGE_DAYS = 7


def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return unescape(re.sub(r"\s+", " ", text)).strip()


def collect_news():
    articles = []
    seen = set()

    for category, search in SEARCHES.items():
        query = f"{search} when:{MAX_AGE_DAYS}d"

        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(query)
            + "&hl=en-US&gl=US&ceid=US:en"
        )

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(request, timeout=20) as response:
                root = ET.fromstring(response.read())

            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                description = clean_text(
                    item.findtext("description", "")
                )
                date_text = item.findtext("pubDate", "")

                source_element = item.find("source")
                source = (
                    source_element.text
                    if source_element is not None
                    else "Unknown"
                )

                if not title or not link or not date_text:
                    continue

                try:
                    published = parsedate_to_datetime(date_text)
                    if published.tzinfo is None:
                        published = published.replace(
                            tzinfo=timezone.utc
                        )
                except (ValueError, TypeError):
                    continue

                age = datetime.now(timezone.utc) - published

                if age > timedelta(days=MAX_AGE_DAYS):
                    continue

                # Remove duplicate headlines.
                key = title.lower().strip()

                if key in seen:
                    continue

                seen.add(key)

                articles.append({
                    "title": clean_text(title),
                    "link": link,
                    "description": description[:500],
                    "source": source,
                    "category": category,
                    "published": published.isoformat(),
                    "age_hours": round(age.total_seconds() / 3600, 1)
                })

            print(f"Collected: {category}")

        except Exception as error:
            print(f"Could not collect {category}: {error}")

    # Newest stories first.
    articles.sort(key=lambda x: x["published"], reverse=True)

    articles = articles[:MAX_ARTICLES]

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(articles),
        "articles": articles
    }

    with open("feed.json", "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"\nFinished! Collected {len(articles)} articles.")


if __name__ == "__main__":
    collect_news()
