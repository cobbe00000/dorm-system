from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import json
import traceback
from datetime import datetime as dt, timedelta, timezone

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"
TEACHER_PWD = "0800092000"

# 🎯 改用 Python 內建標準 timezone 鎖定 +8 台灣時區，Render 100% 穩定開機、不需安裝外部套件
tw_tz = timezone(timedelta(hours=8))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = None
INIT_ERROR = None

try:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("Render 後台尚未設定環境變數！")
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    INIT_ERROR = f"🚨 資料庫連線失敗：\n{traceback.format_exc()}"

# ==============================================================================

def get_week_info(target_date):
    """🎯 精準對齊台灣習慣（週日算新的一週開始）的計算公式"""
    # weekday() 預設週一是 0，週日是 6。我們將其轉換為：週日是 0，週一是 1 ... 週六是 6
    idx = (target_date.weekday() + 1) % 7
    sun = target_date - timedelta(days=idx)
    sat = target_date + timedelta(days=(6 - idx))
    return sun.strftime("%Y-%m-%d"), sun.strftime("%Y-%m-%d"), sat.strftime("%Y-%m-%d")

def get_deadline_by_week(week_id, default_sat_str):
    try:
        res = supabase.table("settings").select("*").eq("week_id", week_id).execute()
        if res.data:
            return res.data[0].get("deadline")
    except:
        pass
    return f"{default_sat_str} 23:59"

# ==============================================================================

@app.errorhandler(500)
def internal_server_error(e):
    return f"<pre>{INIT_ERROR if INIT_ERROR else traceback.format_exc()}</pre>", 500

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
            "timestamp": dt.now(tw_tz).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            supabase.table("applications").upsert(payload, on_conflict="student_id,target_date").execute()
            return jsonify({"status": "success", "message": "📥 資料已安全存入雲端資料庫！"})
        except Exception as e:
            err_msg = str(e)
            if "row-level security" in err_msg or "42501" in err_msg:
                return jsonify({
                    "status": "error", 
                    "message": "Waktu pendaftaran telah habis!\nThời gian đăng ký đã hết!\n⚠️ 登記時間已過或本週尚未開放，請找老師登記！"
                })
            return jsonify({"status": "error", "message": err_msg})

    # 學生端日期：精準取得台灣今日
    today = dt.now(tw_tz)
    _, sun_str, sat_str = get_week_info(today)
    
    return render_template("student.html", 
                           student_id=session.get("student_id"), 
                           student_name=session.get("student_name"),
                           week_start=sun_str,
                           week_end=sat_str)

@app.route("/teacher/save_settings", methods=["POST"])
def save_settings():
    if session.get("role") != "teacher": return redirect(url_for("login"))
    target_week_id = request.form.get("week_id")
    new_dl = f"{request.form.get('deadline_date')} {request.form.get('deadline_time')}"
    try:
        supabase.table("settings").upsert({"week_id": target_week_id, "deadline": new_dl}).execute()
    except Exception as e:
        pass
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/unlock_week", methods=["POST"])
def unlock_week():
    if session.get("role") != "teacher": return redirect(url_for("login"))
    target_week_id = request.form.get("week_id")
    far_deadline = request.form.get("default_sat") + " 23:59"
    try:
        supabase.table("settings").upsert({"week_id": target_week_id, "deadline": far_deadline}).execute()
    except:
        pass
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher")
def teacher_dashboard():
    if INIT_ERROR: return internal_server_error(None)
    if session.get("role") != "teacher": return redirect(url_for("login"))
    
    today = dt.now(tw_tz)
    next_week_date = today + timedelta(days=7)
    
    this_week_id, this_sun, this_sat = get_week_info(today)
    next_week_id, next_sun, next_sat = get_week_info(next_week_date)
    
    this_deadline = get_deadline_by_week(this_week_id, this_sat)
    next_deadline = get_deadline_by_week(next_week_id, next_sat)
    
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
        
    week_settings = {
        "this_week": {"id": this_week_id, "range": f"{this_sun} ~ {this_sat}", "deadline": this_deadline, "sat": this_sat},
        "next_week": {"id": next_week_id, "range": f"{next_sun} ~ {next_sat}", "deadline": next_deadline, "sat": next_sat}
    }
        
    return render_template("teacher.html", 
                           applications=sorted(apps, key=lambda x: x.get("student_id", "")), 
                           week_settings=week_settings)

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
