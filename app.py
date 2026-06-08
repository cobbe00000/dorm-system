from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime as dt, timezone, timedelta

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"

DB_FILE = "data.json"
TEACHER_PWD = "0800092000"
tw_tz = timezone(timedelta(hours=8))

def load_data():
    # 🎯 預設狀態改為 system_status: "open" (開啟)
    if not os.path.exists(DB_FILE):
        return {"settings": {"system_status": "open"}, "applications": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # 防呆：如果舊資料沒有 settings 或 system_status，自動補上
        if "settings" not in data:
            data["settings"] = {"system_status": "open"}
        if "system_status" not in data["settings"]:
            data["settings"]["system_status"] = "open"
        return data

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        if role == "teacher":
            password = request.form.get("password")
            if password == TEACHER_PWD:
                session["role"] = "teacher"
                return redirect(url_for("teacher_dashboard"))
            else:
                return render_template("login.html", error="老師密碼錯誤！")
        else:
            # 🎯 學生登入檢查：一鍵鎖定檢查
            db = load_data()
            if db["settings"].get("system_status") == "locked":
                return render_template("login.html", error="🔒 目前系統已鎖定，暫不開放登記！")
                
            session["role"] = "student"
            session["student_id"] = request.form.get("student_id")
            session["student_name"] = request.form.get("student_name")
            return redirect(url_for("student_form"))
            
    return render_template("login.html")

@app.route("/student", methods=["GET", "POST"])
def student_form():
    if session.get("role") != "student":
        return redirect(url_for("login"))
        
    if request.method == "POST":
        # 🎯 學生送出假單檢查：一鍵鎖定檢查
        db = load_data()
        if db["settings"].get("system_status") == "locked":
            return jsonify({"status": "error", "message": "🔒 系統剛剛已鎖定，暫不開放登記！"})

        form_data = request.form.to_dict()
        form_data["student_id"] = session["student_id"]
        form_data["student_name"] = session["student_name"]
        form_data["timestamp"] = dt.now(tw_tz).strftime("%Y-%m-%d %H:%M:%S")
        
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

        db["applications"] = [
            a for a in db["applications"] 
            if not (a["student_id"] == session["student_id"] and a.get("target_date") == target_date)
        ]
        
        db["applications"].append(form_data)
        save_data(db)
        
        return jsonify({"status": "success", "message": f"📥 {target_date} 的資料填報成功！"})

    return render_template("student.html", student_id=session.get("student_id"), student_name=session.get("student_name"))

@app.route("/teacher")
def teacher_dashboard():
    if session.get("role") != "teacher":
        return redirect(url_for("login"))
    db = load_data()
    apps = sorted(db["applications"], key=lambda x: x["student_id"])
    return render_template("teacher.html", applications=apps, settings=db["settings"])

# 🎯 全新的一鍵開關路由
@app.route("/teacher/toggle_status", methods=["POST"])
def toggle_status():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    db = load_data()
    current_status = db["settings"].get("system_status", "open")
    
    # 切換狀態
    if current_status == "open":
        db["settings"]["system_status"] = "locked"
    else:
        db["settings"]["system_status"] = "open"
        
    save_data(db)
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/update_status", methods=["POST"])
def update_status():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    student_id = request.form.get("student_id")
    target_date = request.form.get("target_date")
    status = request.form.get("status")
    db = load_data()
    for app in db["applications"]:
        if app["student_id"] == student_id and app.get("target_date") == target_date:
            app["teacher_status"] = status
            break
    save_data(db)
    return jsonify({"status": "success"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
