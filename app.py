from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import json
import traceback
from datetime import datetime as dt, timedelta
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

def get_current_week_id():
    """🎯 自動計算當下時間屬於一年中的第幾週，以此作為每週鎖定的唯一 ID (格式: YYYY-WW)"""
    today = dt.now()
    # 習慣上以週日為一週的開始：如果今天是一週的開始(週日為0, 週六為6)
    # Python 的 isocalendar() 預設週一是 1，這裡我們轉換成符合台灣學校習慣的週日算新的一週
    idx = (today.weekday() + 1) % 7
    sun_of_this_week = today - timedelta(days=idx)
    return sun_of_this_week.strftime("%Y-w%U")

def get_deadline():
    """🎯 讀取『本週』的截止日期，如果本週老師還沒設定，預設就是這週六的 23:59 (即自動解除上一週的鎖)"""
    week_id = get_current_week_id()
    try:
        res = supabase.table("settings").select("*").eq("week_id", week_id).execute()
        if res.data:
            return res.data[0].get("deadline")
    except:
        pass
    
    # 如果進入了新的一週，而老師還沒設定截止，預設就給他本週六的最後一秒（等於對新的一週自動開放登記）
    today = dt.now()
    idx = (today.weekday() + 1) % 7
    sat_of_this_week = today + timedelta(days=(6 - idx))
    return sat_of_this_week.strftime("%Y-%m-%d 23:59")

# ==============================================================================

@app.errorhandler(500)
def internal_server_error(e):
    err = traceback.format_exc()
    display_err = INIT_ERROR if INIT_ERROR else err
    return f"""
    <div style="font-family:sans-serif; padding:20px; border:3px solid red; background:#fff5f5; border-radius:8px;">
        <h2 style="color:red; margin-top:0;">🚨 系統連線發生問題</h2>
        <pre style="background:#222; color:#fff; padding:15px; border-radius:5px; overflow-x:auto;">{display_err}</pre>
        <br>
        <a href="/" style="background:gray; color:white; padding:10px 15px; text-decoration:none; border-radius:5px;">返回首頁</a>
    </div>
    """, 500

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
            if form_data.get("work_place") == "其他":
                form_data["work_place"] = form_data.get("work_place_other", "其他外派")
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
        
        try:
            supabase.table("applications").upsert(payload, on_conflict="student_id,target_date").execute()
            return jsonify({
                "status": "success", 
                "message": "📥 資料已安全存入雲端資料庫！"
            })
        except Exception as e:
            err_msg = str(e)
            # 🎯 學生端：當撞到 RLS 週鎖定限制時，噴出三語溫馨提示
            if "row-level security" in err_msg or "42501" in err_msg:
                multilingual_msg = (
                    "Waktu pendaftaran telah habis, silakan hubungi guru secara langsung!\n"
                    "Thời gian đăng ký đã hết, vui lòng gặp trực tiếp giáo viên để đăng ký!\n"
                    "⚠️ 登記時間已過，請親自找老師登記！"
                )
                return jsonify({
                    "status": "error", 
                    "message": multilingual_msg
                })
            return jsonify({"status": "error", "message": err_msg})

    # 🎯 自動計算學生「今天登入時」所在的本週一到週日範圍，供前端畫面的日期做自動限制與顯示
    today = dt.now()
    idx = (today.weekday() + 1) % 7
    sun = (today - timedelta(days=idx)).strftime("%Y-%m-%d")
    sat = (today + timedelta(days=(6 - idx))).strftime("%Y-%m-%d")
    
    return render_template("student.html", 
                           student_id=session.get("student_id"), 
                           student_name=session.get("student_name"),
                           week_start=sun,
                           week_end=sat)

@app.route("/teacher/save_settings", methods=["POST"])
def save_settings():
    if INIT_ERROR: return internal_server_error(None)
    if session.get("role") != "teacher": return redirect(url_for("login"))
    
    new_dl = f"{request.form.get('deadline_date')} {request.form.get('deadline_time')}"
    week_id = get_current_week_id()
    
    try:
        # 將設定綁定在本週的 week_id 上
        supabase.table("settings").upsert({"id": 1, "week_id": week_id, "deadline": new_dl}, on_conflict="id").execute()
    except Exception as e:
        err_msg = str(e)
        if "row-level security" in err_msg or "42501" in err_msg:
            return """
            <script>
                alert("Waktu pendaftaran telah habis, silakan hubungi guru secara langsung!\\nThời gian đăng ký đã hết, vui lòng gặp trực tiếp giáo viên để đăng ký!\\n⚠️ 登記時間已過，請親自找老師登記！");
                window.location.href = "/teacher";
            </script>
            """
    return redirect(url_for("teacher_dashboard"))

# 🎯 新增功能：老師一鍵主動「解鎖本週」的功能路徑
@app.route("/teacher/unlock_current_week", methods=["POST"])
def unlock_current_week():
    if session.get("role") != "teacher": return redirect(url_for("login"))
    week_id = get_current_week_id()
    # 做法：直接把截止時間設到遙遠的未來或這週的最後一秒，讓 RLS 安全檢查直接放行
    today = dt.now()
    idx = (today.weekday() + 1) % 7
    sat_of_this_week = today + timedelta(days=(6 - idx))
    far_deadline = sat_of_this_week.strftime("%Y-%m-%d 23:59")
    try:
        supabase.table("settings").upsert({"id": 1, "week_id": week_id, "deadline": far_deadline}, on_conflict="id").execute()
    except:
        pass
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/update_status", methods=["POST"])
def update_status():
    if session.get("role") != "teacher": return jsonify({"status": "error", "message": "權限不足"})
    
    sid = request.form.get("student_id")
    tdate = request.form.get("target_date")
    status = request.form.get("status")
    try:
        supabase.table("applications").update({"teacher_status": status}).eq("student_id", sid).eq("target_date", tdate).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

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
