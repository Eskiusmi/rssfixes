
import json, os, re, time, requests, feedparser, difflib, csv
from datetime import datetime, timedelta
from dateutil import parser as date_parser

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama3-8b-8192"
HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

HOURS_WINDOW = 24
DB_FILE = "rss_db.json"
WHITELIST_FILE = "university_whitelist.csv"

DIMENSION_ORDER = ["教育关联度", "热度与冲击力", "新颖性与视觉性", "延展性与深度", "受众匹配度"]
WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

def load_whitelist():
    if not os.path.exists(WHITELIST_FILE):
        print("⚠️ 未找到名单文件 university_whitelist.csv，默认不过滤")
        return None
    with open(WHITELIST_FILE, encoding="utf-8") as f:
        return set(row["university"].strip() for row in csv.DictReader(f))

def make_prompt(title, summary):
    return f"""你是教育领域内容创作者的智能助手，请对以下新闻进行多维度评分和解释。
要求：
- 对每个维度打 1~10 分，并写一句理由说明。
- 最后生成英文摘要，并计算加权平均的综合评分。
维度：
1. 教育关联度
2. 热度与冲击力
3. 新颖性与视觉性
4. 延展性与深度
5. 受众匹配度
请返回 JSON，如下格式：
{{
  "维度评分": {{
    "教育关联度": {{"分数": 8, "说明": "与教育政策强相关"}},
    ...
  }},
  "summary": "...",
  "score": 8.2
}}
新闻标题: {title}
新闻摘要: {summary}
"""

def evaluate(title, summary):
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": make_prompt(title, summary)}],
        "temperature": 0.3
    }
    try:
        r = requests.post(f"{GROQ_API_BASE}/chat/completions", headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.S)
        data = json.loads(m.group(0)) if m else {}
        dims = data.get("维度评分", {})
        edu_score = dims.get("教育关联度", {}).get("分数", 0)
        if edu_score < 6:
            print(f"⚠️ 教育关联度过低（{edu_score}），忽略")
            return None
        score = sum((dims[d]["分数"] if isinstance(dims.get(d), dict) else 0) * w for d, w in zip(DIMENSION_ORDER, WEIGHTS))
        return {"score": round(score, 2), "summary": data.get("summary", ""), "dimensions": dims}
    except Exception as e:
        print("❌ Groq error:", e)
        return None

def parse_datetime_safe(raw):
    try:
        dt = date_parser.parse(raw)
        if dt.year < 2020:
            return datetime.utcnow().replace(tzinfo=None)
        return dt.replace(tzinfo=None)
    except:
        return datetime.utcnow().replace(tzinfo=None)

def is_similar(t1, t2, threshold=0.4):
    return difflib.SequenceMatcher(None, t1, t2).ratio() >= threshold

def llm_is_duplicate(t1, s1, t2, s2):
    prompt = f"""
判断以下两个新闻是否描述的是同一事件，不考虑语言风格或表达方式，只看是否报道的是相同事件。
标题1: {t1}
摘要1: {s1}
标题2: {t2}
摘要2: {s2}
返回格式:
{{"same_event": true/false}}
"""
    try:
        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        res = requests.post(f"{GROQ_API_BASE}/chat/completions", headers=HEADERS, json=payload, timeout=30)
        res.raise_for_status()
        txt = res.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", txt, re.S)
        result = json.loads(match.group(0)) if match else {}
        time.sleep(2.1)
        return result.get("same_event", False)
    except Exception as e:
        print("⚠️ LLM 去重失败:", e)
        return False

def deduplicate(items):
    unique = []
    for item in items:
        is_dup = False
        for u in unique:
            if is_similar(item["title"], u["title"], threshold=0.4):
                if llm_is_duplicate(item["title"], item["summary"], u["title"], u["summary"]):
                    if item["published"] < u["published"]:
                        unique.remove(u)
                        unique.append(item)
                    is_dup = True
                    break
        if not is_dup:
            unique.append(item)
    return unique

def fetch_rss(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        print("📥 抓取:", url)
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        print(f"✅ 返回条目数：{len(parsed.entries)}")
        return parsed
    except Exception as e:
        print("❌ 抓取失败:", e)
        return feedparser.parse("")

def load_db():
    if os.path.exists(DB_FILE):
        return json.load(open(DB_FILE, encoding="utf-8"))
    return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def collect(feeds="feeds.json"):
    now = datetime.utcnow().replace(tzinfo=None)
    whitelist = load_whitelist()
    items = []
    for f in json.load(open(feeds, encoding="utf-8")):
        rss = f.get("rss")
        if not rss:
            continue
        parsed = fetch_rss(rss)
        for e in parsed.entries:
            title = e.get("title", "").strip()
            link = e.get("link", "").strip()
            summary = e.get("summary", "") or e.get("content", [{}])[0].get("value", "")
            published_raw = e.get("published", "") or e.get("updated", "") or e.get("created", "")
            pub_time = parse_datetime_safe(published_raw)
            text = f"{title} {summary}"
            if whitelist and not any(uni.lower() in text.lower() for uni in whitelist):
                continue
            if now - pub_time > timedelta(hours=HOURS_WINDOW):
                continue
            items.append({
                "university": f.get("university", "Google Alert"),
                "title": title,
                "link": link,
                "summary": summary,
                "published": pub_time.isoformat()
            })
    print(f"✅ 抓取完成，共收集新闻：{len(items)}")
    return items

def main():
    today = deduplicate(collect())
    print(f"🧠 去重后剩余新闻：{len(today)}")
    results = []
    for item in today:
        print("→ 评分中:", item["title"][:60])
        result = evaluate(item["title"], item["summary"])
        time.sleep(2.1)
        if result:
            item.update(result)
            results.append(item)
    old = load_db()
    combined = deduplicate(results + old)
    now = datetime.utcnow().replace(tzinfo=None)
    fresh = []
    for i in combined:
        try:
            dt = parse_datetime_safe(i["published"])
            if now - dt < timedelta(hours=HOURS_WINDOW):
                fresh.append(i)
        except:
            continue
    save_db(fresh)
    json.dump(fresh, open("evaluated_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"📦 写入 rss_db.json 共 {len(fresh)} 条新闻")
    print("✅ 全部完成")

if __name__ == "__main__":
    main()
