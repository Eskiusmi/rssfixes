from flask import Flask, render_template_string, jsonify
import json, os

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ RSS 服务已部署成功！请访问 /run 启动评估，或访问 /results 查看评分结果"

@app.route("/run")
def run_job():
    try:
        from rss_evaluate import main as run_rss
        run_rss()
        return jsonify({"status": "success", "message": "RSS evaluation complete."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/results")
def results():
    try:
        with open("evaluated_results.json", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"<h2>❌ 无法读取结果：{e}</h2>"

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>News Evaluation Results</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background: #f1f3f6;
                margin: 0;
                padding: 20px;
            }
            .lang-toggle {
                float: right;
                margin-top: -20px;
            }
            .container {
                max-width: 960px;
                margin: auto;
            }
            .card {
                background: white;
                padding: 20px;
                margin: 15px 0;
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }
            .title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .summary {
                margin-top: 10px;
                color: #333;
            }
            .meta {
                color: #555;
                font-size: 14px;
            }
            .score {
                font-size: 16px;
                font-weight: bold;
                color: #0077cc;
            }
            .toggle-btn {
                padding: 5px 10px;
                border: 1px solid #aaa;
                background: #fff;
                border-radius: 5px;
                cursor: pointer;
                margin-left: 10px;
            }
        </style>
        <script>
            function toggleLang(lang) {
                document.querySelectorAll('[data-lang]').forEach(el => {
                    el.style.display = (el.dataset.lang === lang) ? 'block' : 'none';
                });
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1>📊 <span data-lang="en">News Evaluation Results</span><span data-lang="zh" style="display:none;">新闻智能评分结果</span></h1>
            <div class="lang-toggle">
                <span class="toggle-btn" onclick="toggleLang('en')">EN</span>
                <span class="toggle-btn" onclick="toggleLang('zh')">中文</span>
            </div>
            {% for item in items %}
                <div class="card">
                    <div class="title"><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></div>
                    <div class="meta">📅 {{ item.published }} ｜ ⭐ <span class="score">{{ item.score }}</span></div>
                    <div class="summary" data-lang="en">{{ item.summary }}</div>
                    <div class="summary" data-lang="zh" style="display:none;">{{ item.summary | safe }}</div>
                </div>
            {% endfor %}
        </div>
    </body>
    </html>
    '''

    return render_template_string(html, items=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
