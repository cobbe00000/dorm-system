from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import json
import traceback
from datetime import datetime as dt
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"
TEACHER_PWD = "0800092000"

# 🎯 從環境變數讀取 Supabase 的連線資訊
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
INIT_ERROR = None

try:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("Render 後台尚未設定 SUPABASE_URL 或 SUPABASE_KEY 環境變數！")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    INIT_ERROR = f"🚨 Supabase 資料庫連線失敗，詳細日誌：\n{traceback.format_exc()}"

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

def get_deadline():
    try:
        res = supabase.table("settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0].get("deadline", "2026-12-31 23:59")
    except:
        pass
    return "2026-12-31 23:59"

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
        target_date = ""
        if form_data.get("leave_type") == "工讀":
            target_date = form_data.get("work_date")
        elif form_data.get("leave_type") == "省親":
            target_date = form_data.get("fam_start_date")
        elif form_data.get("leave_type") == "回國":
            target_date = form_data.get("go_date")

        payload = {
            "student_id": session["student_id"],
            "student_name": session["student_name"],
            "leave_type": form_data.get("leave_type"),
            "target_date": target_date,
            "details": json.dumps(form_data, ensure_ascii=False),
            "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        supabase.table("applications").upsert(payload, on_conflict="student_id,target_date").execute()
        return jsonify({"status": "success", "message": f"📥 假單已安全存入雲端硬碟！"})

    return render_template("student.html", student_id=session.get("student_id"), student_name=session.get("student_name"))

@app.route("/teacher")
def teacher_dashboard():
    if INIT_ERROR: return internal_server_error(None)
    if session.get("role") != "teacher": return redirect(url_for("login"))
    
    deadline = get_deadline()
    res = supabase.table("applications").select("*").execute()
    
    apps = []
    for item in (res.data if res.data else []):
        try: full_data = json.loads(item["details"])
        except: full_data = {}
        full_data["student_id"] = item["student_id"]
        full_data["student_name"] = item["student_name"]
        full_data["leave_type"] = item["leave_type"]
        full_data["target_date"] = item["target_date"]
        full_data["teacher_status"] = item.get("teacher_status", "待審核")
        apps.append(full_data)
        
    return render_template("teacher.html", applications=sorted(apps, key=lambda x: x.get("student_id", "")), settings={"deadline": deadline})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
