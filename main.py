
from flask import Flask, render_template_string, jsonify
import json, os

app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>✅ 服务已部署，访问 <a href='/evaluate'>/evaluate</a> 查看新闻评分结果</h2>"

@app.route("/evaluate")
def evaluate_and_render():
    try:
        from rss_evaluate import main as run_rss
        run_rss()
    except Exception as e:
        return f"<h2>❌ 运行分析失败：{e}</h2>"

    try:
        with open("evaluated_results.json", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"<h2>❌ 读取结果失败：{e}</h2>"

    try:
        with open("rss_viewer_static_rendered.html", encoding="utf-8") as f:
            html = f.read()
        return render_template_string(html, items=data)
    except Exception as e:
        return f"<h2>❌ 加载页面失败：{e}</h2>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
