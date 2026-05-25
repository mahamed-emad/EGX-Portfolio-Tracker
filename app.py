"""
app.py — نقطة التشغيل الرئيسية
"""

import os
import time
from threading import Thread
import webbrowser  # المكتبة المدمجة لفتح متصفحك الشخصي
from flask import Flask, render_template, send_from_directory
from database.db import bootstrap
from routes.api import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "egx-portfolio-secret-2025")
    app.config["JSON_AS_ASCII"] = False

    app.register_blueprint(api)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


def open_browser():
    """ينتظر ثانيتين حتى يقلع السيرفر، ثم يفتح الرابط كـ Tab جديدة في متصفحك الشخصي"""
    time.sleep(2)
    url = "http://localhost:5000"
    webbrowser.open_new_tab(url)


if __name__ == "__main__":
    bootstrap()
    app = create_app()
    
    # منع التكرار: تشغيل المتصفح مرة واحدة فقط في العملية الأساسية وليس في الـ reloader
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        # تشغيل دالة الفتح في الخلفية كـ Thread منفصل حتى لا تعطل السيرفر
        Thread(target=open_browser).start()

    # تشغيل سيرفر Flask
    app.run(debug=True, host="0.0.0.0", port=5000)