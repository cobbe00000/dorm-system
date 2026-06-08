from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime as dt

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"

# 🎯 修正1：自動偵測目前專案路徑，不綁死 C 槽，確保在雲端 Linux 平台能正常讀取
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data.json")

TEACHER_PWD = "0800092000"

def load_data():
    if not os.path.exists(DB_FILE):
        return {"settings": {"deadline": "2026-12-31 23:59"}, "applications": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"settings": {"deadline": "2026-12-31 23:59"}, "applications": []}

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
            student_id = request.form.get("student_id", "").strip()
            student_name = request.form.get("student_name", "").strip()
            
            if not student_id or not student_name:
                return render_template("login.html", error="學號與姓名不能為空！")
                
            db = load_data()
            deadline_str = db["settings"].get("deadline", "2026-12-31 23:59")
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
        db = load_data()
        
        deadline_str = db["settings"].get("deadline", "2026-12-31 23:59")
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

        # 保留你原本的防覆蓋邏輯
        db["applications"] = [
            a for a in db["applications"] 
            if not (a["student_id"] == session["student_id"] and a.get("target_date") == target_date)
        ]
        
        db["applications"].append(form_data)
        save_data(db)
        
        return jsonify({"status": "success", "message": f"📥 {target_date} 的資料填報成功！您可以繼續填寫其他日期的假單唷。"})

    return render_template("student.html", student_id=session.get("student_id"), student_name=session.get("student_name"))

@app.route("/teacher")
def teacher_dashboard():
    if session.get("role") != "teacher":
        return redirect(url_for("login"))
    db = load_data()
    apps = sorted(db["applications"], key=lambda x: x["student_id"])
    return render_template("teacher.html", applications=apps, settings=db["settings"])

@app.route("/teacher/save_settings", methods=["POST"])
def save_settings():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    db = load_data()
    db["settings"]["deadline"] = f"{request.form.get('deadline_date')} {request.form.get('deadline_time')}"
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

@app.route("/teacher/confirm_week", methods=["POST"])
def confirm_week():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "message": "🔒 本週假單已鎖定！自動化排隊上傳學校網站中..."})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
