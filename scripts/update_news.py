import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
today = datetime.now(KST).strftime('%Y-%m-%d')

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
        if not title:
            continue
        items.append({
            'title': title,
            'summary': desc[:200] if desc else title,
            'source': '연합뉴스'
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
    cutoff = (datetime.now(KST) - timedelta(days=30)).strftime('%Y-%m-%d')
    data = {k: v for k, v in sorted(data.items()) if k >= cutoff}
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'완료: {today} 뉴스 업데이트')
else:
    print('기사를 가져오지 못해 업데이트 건너뜀')
