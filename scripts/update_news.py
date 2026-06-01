import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)
today = now_kst.strftime('%Y-%m-%d')

# Read configured time from settings.json
with open('settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)

configured_hour   = settings.get('hour', 7)
configured_minute = settings.get('minute', 0)

# Read existing news data
data_path = 'news_data.json'
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check if today's data already has RSS-fetched articles (has 'url' field)
today_data = data.get(today, {})
already_fetched = any(
    any(a.get('url') for a in today_data.get(cat, []))
    for cat in ['trend', 'social', 'it', 'global']
)

if already_fetched:
    print(f'오늘({today}) RSS 데이터 이미 있음 — 건너뜀')
    sys.exit(0)

# Only run after the configured time
now_total    = now_kst.hour * 60 + now_kst.minute
target_total = configured_hour * 60 + configured_minute

if now_total < target_total:
    print(f'현재 {now_kst.strftime("%H:%M")} KST — 설정 시간({configured_hour:02d}:{configured_minute:02d}) 전 — 건너뜀')
    sys.exit(0)

print(f'뉴스 업데이트 시작 ({now_kst.strftime("%H:%M")} KST, 설정: {configured_hour:02d}:{configured_minute:02d})')

FEEDS = {
    'trend':  'https://www.yna.co.kr/RSS/entertainment.xml',
    'social': 'https://www.yna.co.kr/RSS/economy.xml',
    'it':     'https://www.yna.co.kr/RSS/it.xml',
    'global': 'https://www.yna.co.kr/RSS/international.xml',
}

def fetch_rss(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

def parse_items(xml_data, count=3):
    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall('.//item')[:count]:
        title = item.findtext('title', '').strip()
        desc = re.sub(r'<[^>]+>', '', item.findtext('description', '')).strip()
        desc = re.sub(r'\s+', ' ', desc)
        link = item.findtext('link', '').strip()
        if not title:
            continue
        items.append({
            'title': title,
            'summary': desc[:200] if desc else title,
            'source': '연합뉴스',
            'url': link
        })
    return items

fetched = {}
for cat, url in FEEDS.items():
    try:
        xml = fetch_rss(url)
        articles = parse_items(xml, 3)
        fetched[cat] = articles
        print(f'  {cat}: {len(articles)}개')
    except Exception as e:
        print(f'  {cat}: 실패 - {e}')
        fetched[cat] = today_data.get(cat, [])

if any(fetched[c] for c in fetched):
    data[today] = fetched
    cutoff = (now_kst - timedelta(days=30)).strftime('%Y-%m-%d')
    data = {k: v for k, v in sorted(data.items()) if k >= cutoff}
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'완료: {today} 뉴스 업데이트')
else:
    print('기사를 가져오지 못해 업데이트 건너뜀')
