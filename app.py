import os
from flask import Flask, jsonify, render_template_string
import pymysql

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "emeralddb")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "accounts")
PORT = int(os.getenv("PORT", 8080))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmeraldFlow Application</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #0d1b2a, #1b263b);
            color: #e0e1dd;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 40px;
            max-width: 480px;
            width: 90%;
            text-align: center;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        h1 {
            color: #00f5d4;
            margin-bottom: 8px;
            font-size: 2rem;
        }
        p {
            color: #a0aec0;
            line-height: 1.6;
        }
        .badge {
            display: inline-block;
            background-color: #00b4d8;
            color: #03045e;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 12px;
        }
        .links {
            margin-top: 24px;
            display: flex;
            justify-content: center;
            gap: 16px;
        }
        .links a {
            color: #00f5d4;
            text-decoration: none;
            padding: 8px 16px;
            border: 1px solid #00f5d4;
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        .links a:hover {
            background-color: #00f5d4;
            color: #0d1b2a;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>EmeraldFlow</h1>
        <p>DevOps Application running on Python / Flask & Gunicorn.</p>
        <div class="badge">Status: Online</div>
        <div class="links">
            <a href="/health">Health API</a>
            <a href="/db-status">Database Check</a>
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route("/health")
def health():
    return jsonify({
        "status": "UP",
        "service": "emeraldflow-app",
        "runtime": "python"
    }), 200


@app.route("/db-status")
def db_status():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connect_timeout=3
        )
        connection.close()
        return jsonify({
            "database": "connected",
            "host": DB_HOST,
            "name": DB_NAME
        }), 200
    except Exception as e:
        return jsonify({
            "database": "disconnected",
            "host": DB_HOST,
            "error": str(e)
        }), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
