from flask import Flask, jsonify, send_file
from rss_evaluate import main as run_rss
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ RSS 服务已部署成功！请访问 /run 启动评估，或访问 /results 查看最新 JSON 结果。"

@app.route("/run", methods=["GET"])
def run_job():
    try:
        run_rss()
        return jsonify({"status": "success", "message": "RSS evaluation complete."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/results", methods=["GET"])
def view_results():
    if os.path.exists("evaluated_results.json"):
        return send_file("evaluated_results.json", mimetype="application/json")
    else:
        return jsonify({"status": "error", "message": "No results file found."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
