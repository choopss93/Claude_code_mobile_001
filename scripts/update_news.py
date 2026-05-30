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

# Check if current time is within [configured - 10min, configured)
now_total   = now_kst.hour * 60 + now_kst.minute
target_total = configured_hour * 60 + configured_minute
window_start = target_total - 10

if not (window_start <= now_total < target_total):
    print(f'현재 {now_kst.strftime("%H:%M")} KST — 업데이트 윈도우 아님 (설정: {configured_hour:02d}:{configured_minute:02d})')
    sys.exit(0)

print(f'업데이트 윈도우 진입 — 뉴스 가져오는 중...')

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

data_path = 'news_data.json'
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

today_data = {}
for cat, url in FEEDS.items():
    try:
        xml = fetch_rss(url)
        articles = parse_items(xml, 3)
        today_data[cat] = articles
        print(f'  {cat}: {len(articles)}개')
    except Exception as e:
        print(f'  {cat}: 실패 - {e}')
        today_data[cat] = data.get(today, {}).get(cat, [])

if any(today_data[c] for c in today_data):
    data[today] = today_data
    cutoff = (now_kst - timedelta(days=30)).strftime('%Y-%m-%d')
    data = {k: v for k, v in sorted(data.items()) if k >= cutoff}
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'완료: {today} 뉴스 업데이트')
else:
    print('기사를 가져오지 못해 업데이트 건너뜀')
