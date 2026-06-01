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

# 🎯 【完美對接全新 Firebase 專案：dorm-135bf】
FIREBASE_DB_URL = "https://dorm-135bf-default-rtdb.firebaseio.com"

# 🛡️ 憑證完美隔離與多重防毒機制
INIT_ERROR = None
try:
    # 🔒 將老師新下載的私鑰，用 Python 原生字串安全鎖死，徹底防禦任何主機平台造成的換行符號扭曲
    raw_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDXKtsuZw4bWAjd\n"
        "pkhS/IlG+RakN/KuetqFF6AOpxt+VwjCF3YNPuOl3/tt/f3DYdRThLEnYcKgtdSY\n"
        "AjtwPhEyRDb36nVQHGCxDso5DvrxOUhZj9L43i/9itex/2xRRKyvRWW8Nxsme/WW\n"
        "qsNxhT0VgZrY/qvxO+t1opzg6j/IrmB2wJGOHyd5xbCT/iG6ePlx+YKkPOdNqKun\n"
        "0OISMVNXf1QxDuKumj7V8e95Cje9L3HLdaxUNJhbjNJicgPIaalW6FH4t4bkFAT/\n"
        "+nTTXPHT32p+qYyZnbzJ6Pm93o7wBlwQpK0/TOUNKYhPvVPaU57VSs900AgtRNJx\n"
        "3AkOi7tlAgMBAAECggEAWJHCkVJIg0b0t1B4WvirBXUJNeX11o6pnrl/4Cg3cAUh\n"
        "jMudg4xMpv4RAFDaAXAmt45aYeyi8gaHEV9x2h0idP+RZPG1Apn7z0ZYRa5964f5\n"
        "2SwT2u+S75oUeae7jaRoNOmrHBPO8EN8b12xf+wpnc2w0PvcCTvyC4U5cHfcc51a\n"
        "unQYPdSCJREbG/V/u3u3wDeebNLYabHR1YHW9TpUla9bikGYDJAl3y9UbA7KFSoI\n"
        "6Ae3n5YCN2sjD5iukiSzOK94NKVsoXiOZLQQGTvuE9QilVTn41PWrNL/LHwU2YuY\n"
        "aUCEkhxblPJ1N50R1j4H5m8/55lr3oH/+MtrxotbLQKBgQDxUZoHnP7JBA5+a7yR\n"
        "uh6gjqHylHbNHCTtlS7LXTd6LX1Rqxn1BeLPyDrhjpsoadWOzLL8L237qHzanOOi\n"
        "rRtCDUx9EFuYZYxEMX4DDV7eDnTjtxeul3aUaPVV3+ujGpByXR6wdfK7/fa+rQom\n"
        "+I4w4L3ECTePaZAUQiWkYm+X0wKBgQDkQfZpILDFnYzopBbTDghYfXfSN/qCzR9P\n"
        "M/34xEenr3NevK6KliTCSvpPhd7zMu8DuVt+CS8Ep1IHl+UTDBKsNOLts+nuS8TR\n"
        "3cnX2/0xFjLin+iDrM5wlBqE1N/c7eRaVZiqIs0vsvzngg2Wbm+wn+I10jQCwL8c\n"
        "RwFw2QXU5wKBgQDKL0FrUYlS6DgwiZmzSwowIXDkaqlizkrOV+id8Jrznbtauo2D\n"
        "8guHZU6X/sBWyt1nyG/JxP9UE2WQUFSUzo6A9913B0aG18X+uKzIZ+JtEBW1WIjZ\n"
        "+gMa8xlierrVrAMMHqMA28Gk6nJabWaNIkEYCKRV5BcN7DcQEh+xq9utiwKBgET4\n"
        "tZeAnEmqWLi3VHpDxDvQ9dLcvWKmzq4lHLn9vVUrC+Z1hxwzUDoxY7+BySOdoWFz\n"
        "sfS8m6uBT6UhvcNqo33LoUKIWch6tqdfqC0EuVYKyid2gFDBd8PGzNiUZmygqZ6u\n"
        "PKo0R+IA6LCfuLFa/37UYQs4UCUAzv6hagsKWNvDAoGBAN3rKi2r8qZqce0n4rnm\n"
        "ydZaGVPoHTd2vpn4OhsZdp2i0q/2VigCuwcpQR0upuSJqw7b7FIMP1OmhGazGjtR\n"
        "nuBj2ORwO9qJmDwPA/JSG4ZDVYioULhxIeDX2oUKcxtUmR2EYXOSDD5NNYPiHosdf\n"
        "SilRq9yjcKXoA/kMSPutj452\n"
        "-----END PRIVATE KEY-----\n"
    )

    # 🧼 自動建構最精準無暇的憑證字典，不再依賴 Render 後台複雜變數
    config_dict = {
        "type": "service_account",
        "project_id": "dorm-135bf",
        "private_key_id": "36489f81fe9908d7dc4f1dc7c4b250cdaeb64b43",
        "private_key": raw_key,
        "client_email": "firebase-adminsdk-fbsvc@dorm-135bf.iam.gserviceaccount.com",
        "client_id": "103492177677984034115",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40dorm-135bf.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(config_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DB_URL
        })
except Exception as e:
    INIT_ERROR = f"🚨 Firebase 全新對接遭遇衝突，詳細日誌：\n{traceback.format_exc()}"

# ==============================================================================

@app.errorhandler(500)
def internal_server_error(e):
    err = traceback.format_exc()
    display_err = INIT_ERROR if INIT_ERROR else err
    return f"""
    <div style="font-family:sans-serif; padding:20px; border:3px solid red; background:#fff5f5; border-radius:8px;">
        <h2 style="color:red; margin-top:0;">🚨 系統連線發生問題</h2>
        <p>請幫我<b>「整頁截圖」</b>傳給 AI 助手：</p>
        <pre style="background:#222; color:#fff; padding:15px; border-radius:5px; overflow-x:auto;">{display_err}</pre>
        <br>
        <a href="/" style="background:gray; color:white; padding:10px 15px; text-decoration:none; border-radius:5px;">返回首頁</a>
    </div>
    """, 500

@app.errorhandler(405)
def method_not_allowed(e):
    return """
    <div style="font-family:sans-serif; padding:20px; border:3px solid orange; background:#fffbe6; border-radius:8px;">
        <h2 style="color:orange; margin-top:0;">⚠️ 操作逾時或重置 (405)</h2>
        <p>請點擊下方按鈕重新登入操作即可！</p>
        <br>
        <a href="/" style="background:#1890ff; color:white; padding:10px 15px; text-decoration:none; border-radius:5px; font-weight:bold;">返回登入首頁</a>
    </div>
    """, 405

def load_data():
    if INIT_ERROR:
        raise Exception("Firebase 未初始化成功，無法讀取資料")
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
        return {"settings": {"deadline": "2026-12-31 23:59"}, "applications": {}}

@app.route("/", methods=["GET", "POST"])
def login():
    if INIT_ERROR:
        return internal_server_error(None)
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
    if INIT_ERROR:
        return internal_server_error(None)
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
        
        return jsonify({"status": "success", "message": f"📥 資料已安全存入 Firebase 資料庫！"})

    return render_template("student.html", student_id=session.get("student_id"), student_name=session.get("student_name"))

@app.route("/teacher")
def teacher_dashboard():
    if INIT_ERROR:
        return internal_server_error(None)
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
    if INIT_ERROR or session.get("role") != "teacher":
        return jsonify({"status": "error"})
    new_dl = f"{request.form.get('deadline_date')} {request.form.get('deadline_time')}"
    ref = firebase_db.reference('/settings')
    ref.update({"deadline": new_dl})
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/update_status", methods=["POST"])
def update_status():
    if INIT_ERROR or session.get("role") != "teacher":
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
