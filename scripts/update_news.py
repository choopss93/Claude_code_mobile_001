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

# Skip if today already has RSS-fetched articles (has 'url' field)
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

print(f'뉴스 업데이트 시작 ({now_kst.strftime("%H:%M")} KST)')

# Google News RSS — 연합뉴스 대비 서버 차단 없음
FEEDS = {
    'trend':  'https://news.google.com/rss/search?q=한국+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko',
    'social': 'https://news.google.com/rss/search?q=한국+경제+사회&hl=ko&gl=KR&ceid=KR:ko',
    'it':     'https://news.google.com/rss/search?q=한국+IT+기술+인공지능&hl=ko&gl=KR&ceid=KR:ko',
    'global': 'https://news.google.com/rss/search?q=국제뉴스+세계&hl=ko&gl=KR&ceid=KR:ko',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

def fetch_rss(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def get_link(item):
    # ElementTree에서 <link> 텍스트 추출 (RSS 특수 구조 대응)
    for el in item:
        if el.tag == 'link' or el.tag.endswith('}link'):
            if el.text and el.text.strip().startswith('http'):
                return el.text.strip()
    # fallback: findtext
    link = item.findtext('link', '').strip()
    if link.startswith('http'):
        return link
    # fallback: guid
    guid = item.findtext('guid', '').strip()
    if guid.startswith('http'):
        return guid
    return ''

def parse_items(xml_data, count=3):
    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall('.//item'):
        title = item.findtext('title', '').strip()
        # Google News title에서 " - 출처" 분리
        source = 'Google 뉴스'
        if ' - ' in title:
            parts = title.rsplit(' - ', 1)
            title, source = parts[0].strip(), parts[1].strip()
        desc = re.sub(r'<[^>]+>', '', item.findtext('description', '')).strip()
        desc = re.sub(r'\s+', ' ', desc)
        url = get_link(item)
        if not title or len(title) < 5:
            continue
        items.append({
            'title': title,
            'summary': desc[:200] if desc else title,
            'source': source,
            'url': url
        })
        if len(items) == count:
            break
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

if any(fetched.get(c) for c in fetched):
    data[today] = fetched
    cutoff = (now_kst - timedelta(days=30)).strftime('%Y-%m-%d')
    data = {k: v for k, v in sorted(data.items()) if k >= cutoff}
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'완료: {today} 뉴스 업데이트')
else:
    print('기사를 가져오지 못해 업데이트 건너뜀')
