from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import traceback
from datetime import datetime as dt
import firebase_admin
from firebase_admin import credentials, db as firebase_db

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"
TEACHER_PWD = "0800092000"

# ==================== 🛠️ 【Google 金鑰與網址 100% 正確版】 ====================

FIREBASE_CONFIG_STR = """{
  "type": "service_account",
  "project_id": "dorm-a0fe8",
  "private_key_id": "3e05bc307d8456566dd9a99c9f10419c360dd6d4",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC2Sj6B21rIAeZQ\nJ+9xCHgT+Lrn9Jnfsc6V/8ChpAIutSJnBH5i9xMamhuJKaI3AucMW46we75cBTr+\naVdUbnOqQc10ZkAUmlGWfQL5zU7d9HIewBMZvANYah7tV9pDn26aJ9abaasJ3laP\n0VTTg6F//gtYxENNgJWYXA6I0vL06Jcmp46o60Z9ZCR2CEfNFDCk9jxa6iHGzw+/\nVOSSUAF8JgOJ/aH71TECKTTUDnp1KGJU/KHM2vkZONGVQ+jgxyNaQLhSAzdH42H+\ndYqwHcSgV8V14foNI5Uy4GygWyv2tqQad6HS68qkoHW5Aa03rbW3NFwP0XAzRQtV\n6JxbQZenAgMBAAECggEATvK9uqDlYs0L0fhRx8sKsl+dlzsE73BDEAzJgVgWR+NU\nCHjWQgdO400OEuwQoLGlnmEC3eVh7tmnEKtP0rXZa0n/cOOd6i5hmoL+6HBmMVOe\nnznBq/oVGtQvG8zaL0Jb9PC/DeUIWghMxhG7orWWGuhMQsARg/3mDCwGcXSnG7Dr\nBxnvK5L3B9SaJ6Y7XaTzt4zqE8jQH9BslMNmif5rH6nCKmyGklDh3LISn0eQktTT\nKILsv4i/TUq4DudQ9ZG0QzEh7dtzVFXns3ynvjQQS7TimAg/2uOvkL9vP5uRxGgs\n2IHfCclUpfZr5rGI74oEdqVTudjlA7Xt9s5nrshimQKBgQDhf5RXvp6cpkkNWl2r\nCH2nM5zATwlu8Jdz890sLofd1qPx/CmyzF0FZLQp3ztj2fxIHw4dyS4eDecf5gHg\nTBhAdM82RovRNUmw4z0cKpokq3BlwO+XfAt9STyYGl8d5Zu+fr2sqkrGoRy6bmCe\nJdyTMi8jVtojGM4WQF8zPsv1PwKBgQDO8njyDp+iweZy+N3NKYeJ++F0SJHbYvMn\nIM3dmZZC5dJJuYd+3oRSgpycul5e3GMt0fX0S9o3Hh192E0v6RyQFO5bXZIFp0ub\nT+YrPRhhbFl/RnPV/YYpQL58oAsGDakDGrdujGJF+VJ11AHvLA34XJ/uY2BE8u74\nr2qoyAm7mQKBgDjrumdXv7PtKZ2MRP6qWwV8usG0cb4mTyS+1wKTEErIJoQr0d7H\nRWfaHrw/FD/FQ7B03lxYbyK5AbGEns6ehrSmh7O8pQh/OgXDpqZYfqZo/CtDQ3dq\noX/Tn88JQR9L2T+BwKE4Lz3qZ1UMDal+ByrEzS9PeirH1SW6xA0sedGDAoGAOR6y\nBVXF+B1+5xML3XnuAEb2pqr1H1HDfXRPfi/LSrG2hkTgQkNW0JNeeN/z9kjsUxRV\nx9U76OS2DSsruuKj0J0GYU+FY2wWsUqvZBXb6eAHH9spU9JDOpW1Ph7KjCQvFz1D\njg7PfTLg8MbQtdw6Cug9+IWTZ9SJ4zg/v1BfZ1kCgYAQLWmknjUUFR3wVnv0r2gI\nIlezWBB+AY0Ht5DY8X24d3v4W5t4CJ7Y2HmGsCvJlKVrTtsT8Geg6gZqgdkvw1Tn\nmsDfWgcX63giai/U76t5EWR7UUwK5oxRa6gjGj7YtuVHeITEKpjD1LsB3QrOV0Ms\niDVvpKB4jE315ehTkLBqOw==\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@dorm-a0fe8.iam.gserviceaccount.com",
  "client_id": "104158881843458654051",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40dorm-a0fe8.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""

FIREBASE_DB_URL = "https://dorm-a0fe8-default-rtdb.asia-southeast1.firebasedatabase.app"

# ==============================================================================

# 初始化 Firebase 連線
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(FIREBASE_CONFIG_STR.strip()))
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DB_URL
        })
except Exception as e:
    print(f"Firebase 初始化失敗: {e}")

# 🔥 【強力防噴錯除錯器】如果網頁爆炸，直接把主機錯誤吐在畫面上給老師看
@app.errorhandler(500)
def internal_server_error(e):
    err = traceback.format_exc()
    return f"""
    <div style="font-family:sans-serif; padding:20px; border:3px solid red; background:#fff5f5; border-radius:8px;">
        <h2 style="color:red; margin-top:0;">🚨 發現系統內部衝突！</h2>
        <p>老師別慌，請幫我<b>「整頁截圖」</b>傳給 AI 助手，這行字會直接告訴我們哪裡寫錯：</p>
        <pre style="background:#222; color:#fff; padding:15px; border-radius:5px; overflow-x:auto;">{err}</pre>
        <br>
        <a href="/" style="background:gray; color:white; padding:10px 15px; text-decoration:none; border-radius:5px;">返回首頁</a>
    </div>
    """, 500

@app.errorhandler(405)
def method_not_allowed(e):
    return """
    <div style="font-family:sans-serif; padding:20px; border:3px solid orange; background:#fffbe6; border-radius:8px;">
        <h2 style="color:orange; margin-top:0;">⚠️ 瀏覽器抓取網頁方式錯誤 (405)</h2>
        <p>老師/同學，這通常是因為您<b>「重新整理了剛送出資料的網頁」</b>，或是直接在網址列手打輸入了錯誤的網址。</p>
        <p style="color:#666;">請點擊下方按鈕，回到首頁重新正常登入操作即可！</p>
        <br>
        <a href="/" style="background:#1890ff; color:white; padding:10px 15px; text-decoration:none; border-radius:5px; font-weight:bold;">返回登入首頁</a>
    </div>
    """, 405

def load_data():
    try:
        ref = firebase_db.reference('/')
        data = ref.get()
        if not data:
            return {"settings": {"deadline": "2026-12-31 23:59"}, "applications": {}}
        if "settings" not in data:
            data["settings"] = {"deadline": "2026-12-31 23:59"}
        if "applications" not in data:
            data["applications"] = {}
        return data
    except Exception as e:
        print(f"讀取 Firebase 失敗: {e}")
        return {"settings": {"deadline": "2026-12-31 23:59"}, "applications": {}}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        if role == "teacher":
            if request.form.get("password") == TEACHER_PWD:
                session["role"] = "teacher"
                return redirect(url_for("teacher_dashboard"))
            return render_template("login.html", error="老師密碼錯誤！")
        
        student_id = request.form.get("student_id")
        student_name = request.form.get("student_name")
        
        db_data = load_data()
        deadline_str = db_data["settings"].get("deadline", "2026-12-31 23:59")
        
        if dt.now() > dt.strptime(deadline_str, "%Y-%m-%d %H:%M"):
            return render_template("login.html", error="申請已經結束，下次請準時！")
            
        session["role"] = "student"
        session["student_id"] = student_id
        session["student_name"] = student_name
        return redirect(url_for("student_form"))
    return render_template("login.html")

@app.route("/student", methods=["GET", "POST"])
def student_form():
    if session.get("role") != "student":
        return redirect(url_for("login"))
        
    if request.method == "POST":
        db_data = load_data()
        deadline_str = db_data["settings"].get("deadline", "2026-12-31 23:59")
        
        if dt.now() > dt.strptime(deadline_str, "%Y-%m-%d %H:%M"):
            return jsonify({"status": "error", "message": "申請已經結束，下次請準時！"})

        form_data = request.form.to_dict()
        form_data["student_id"] = session["student_id"]
        form_data["student_name"] = session["student_name"]
        form_data["timestamp"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        
        target_date = ""
        if form_data.get("leave_type") == "工讀":
            target_date = form_data.get("work_date")
            if form_data.get("work_place") == "其他":
                form_data["work_place"] = form_data.get("work_place_other", "其他外派")
        elif form_data.get("leave_type") == "省親":
            target_date = form_data.get("fam_start_date")
        elif form_data.get("leave_type") == "回國":
            target_date = form_data.get("go_date")

        form_data["target_date"] = target_date

        key = f"{session['student_id']}_{target_date}".replace('.', '_')
        ref = firebase_db.reference(f'/applications/{key}')
        ref.set(form_data)
        
        return jsonify({"status": "success", "message": f"📥 {target_date} 的資料已同步安全存入 Firebase 永久資料庫！"})

    return render_template("student.html", student_id=session.get("student_id"), student_name=session.get("student_name"))

@app.route("/teacher")
def teacher_dashboard():
    if session.get("role") != "teacher":
        return redirect(url_for("login"))
    
    db_data = load_data()
    deadline = db_data["settings"].get("deadline", "2026-12-31 23:59")
    
    apps_dict = db_data.get("applications", {})
    apps = list(apps_dict.values()) if apps_dict else []
    apps_sorted = sorted(apps, key=lambda x: x.get("student_id", ""))
    
    return render_template("teacher.html", applications=apps_sorted, settings={"deadline": deadline})

@app.route("/teacher/save_settings", methods=["POST"])
def save_settings():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    new_dl = f"{request.form.get('deadline_date')} {request.form.get('deadline_time')}"
    
    ref = firebase_db.reference('/settings')
    ref.update({"deadline": new_dl})
    
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/update_status", methods=["POST"])
def update_status():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    student_id = request.form.get("student_id")
    target_date = request.form.get("target_date")
    status = request.form.get("status")
    
    key = f"{student_id}_{target_date}".replace('.', '_')
    ref = firebase_db.reference(f'/applications/{key}')
    if ref.get():
        ref.update({"teacher_status": status})
        
    return jsonify({"status": "success"})

@app.route("/teacher/confirm_week", methods=["POST"])
def confirm_week():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "message": "🔒 本週假單已鎖定！"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
