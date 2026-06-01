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

FIREBASE_DB_URL = "https://dorm-135bf-default-rtdb.firebaseio.com"

# 🎯 Vercel 最強防呆法：直接讀取同目錄下的金鑰檔案，絕對不會格式出錯！
INIT_ERROR = None
try:
    # 尋找同目錄下的 firebase_key.json
    key_path = os.path.join(os.path.dirname(__file__), 'firebase_key.json')
    
    if not os.path.exists(key_path):
        raise Exception("找不到 firebase_key.json 檔案，請確認是否有上傳到 GitHub！")
        
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DB_URL
        })
except Exception as e:
    INIT_ERROR = f"Firebase 初始化失敗: {traceback.format_exc()}"

# ==============================================================================

@app.errorhandler(500)
def internal_server_error(e):
    err = traceback.format_exc()
    display_err = INIT_ERROR if INIT_ERROR else err
    return f"""
    <div style="font-family:sans-serif; padding:20px; border:3px solid red; background:#fff5f5; border-radius:8px;">
        <h2 style="color:red; margin-top:0;">🚨 系統連線發生問題</h2>
        <pre style="background:#222; color:#fff; padding:15px; border-radius:5px; overflow-x:auto;">{display_err}</pre>
    </div>
    """, 500

def load_data():
    if INIT_ERROR: raise Exception("Firebase 未初始化成功")
    try:
        ref = firebase_db.reference('/')
        data = ref.get()
        return data if data else {"settings": {"deadline": "2026-12-31 23:59"}, "applications": {}}
    except:
        return {"settings": {"deadline": "2026-12-31 23:59"}, "applications": {}}

@app.route("/", methods=["GET", "POST"])
def login():
    if INIT_ERROR: return internal_server_error(None)
    if request.method == "POST":
        role = request.form.get("role")
        if role == "teacher":
            if request.form.get("password") == TEACHER_PWD:
                session["role"] = "teacher"
                return redirect(url_for("teacher_dashboard"))
            return render_template("login.html", error="老師密碼錯誤！")
        
        session["role"] = "student"
        session["student_id"] = request.form.get("student_id")
        session["student_name"] = request.form.get("student_name")
        return redirect(url_for("student_form"))
    return render_template("login.html")

@app.route("/student", methods=["GET", "POST"])
def student_form():
    if INIT_ERROR: return internal_server_error(None)
    if session.get("role") != "student": return redirect(url_for("login"))
    if request.method == "POST":
        form_data = request.form.to_dict()
        form_data["student_id"] = session["student_id"]
        form_data["student_name"] = session["student_name"]
        form_data["timestamp"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        
        target_date = form_data.get("work_date") if form_data.get("leave_type") == "工讀" else form_data.get("fam_start_date")
        form_data["target_date"] = target_date

        key = f"{session['student_id']}_{target_date}".replace('.', '_')
        firebase_db.reference(f'/applications/{key}').set(form_data)
        return jsonify({"status": "success", "message": "📥 資料已安全存入新資料庫！"})
    return render_template("student.html", student_id=session.get("student_id"), student_name=session.get("student_name"))

@app.route("/teacher")
def teacher_dashboard():
    if INIT_ERROR: return internal_server_error(None)
    if session.get("role") != "teacher": return redirect(url_for("login"))
    db_data = load_data()
    apps = list(db_data.get("applications", {}).values())
    return render_template("teacher.html", applications=sorted(apps, key=lambda x: x.get("student_id", "")), settings={"deadline": db_data.get("settings", {}).get("deadline", "2026-12-31 23:59")})

@app.route("/teacher/save_settings", methods=["POST"])
def save_settings():
    new_dl = f"{request.form.get('deadline_date')} {request.form.get('deadline_time')}"
    firebase_db.reference('/settings').update({"deadline": new_dl})
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/update_status", methods=["POST"])
def update_status():
    key = f"{request.form.get('student_id')}_{request.form.get('target_date')}".replace('.', '_')
    firebase_db.reference(f'/applications/{key}').update({"teacher_status": request.form.get("status")})
    return jsonify({"status": "success"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
