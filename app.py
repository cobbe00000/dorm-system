from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime as dt

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data.json")

TEACHER_PWD = "0800092000"

def load_data():
    if not os.path.exists(DB_FILE):
        return {"system_locked": False, "applications": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "system_locked" not in data:
                data["system_locked"] = False
            return data
    except Exception:
        return {"system_locked": False, "applications": []}

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
            # 🎯 學生登入時檢查是否被一鍵鎖定
            db = load_data()
            if db.get("system_locked", False):
                return render_template("login.html", error="系統目前處於鎖定狀態，暫不開放填報！")

            student_id = request.form.get("student_id", "").strip()
            student_name = request.form.get("student_name", "").strip()
            
            if not student_id or not student_name:
                return render_template("login.html", error="學號與姓名不能為空！")
                
            session["role"] = "student"
            session["student_id"] = student_id
            session["student_name"] = student_name
            return redirect(url_for("student_form"))
            
    return render_template("login.html")

@app.route("/student", methods=["GET", "POST"])
def student_form():
    if session.get("role") != "student":
        return redirect(url_for("login"))
        
    # 🎯 防止學生繞過前端直接送出資料，後端再次檢查鎖定狀態
    db = load_data()
    if db.get("system_locked", False):
        if request.method == "POST":
            return jsonify({"status": "error", "message": "系統目前處於鎖定狀態，暫不開放填報！"})
        else:
            session.clear()
            return redirect(url_for("login"))

    if request.method == "POST":
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
    return render_template("teacher.html", applications=apps, system_locked=db.get("system_locked", False))

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

@app.route("/teacher/delete_application", methods=["POST"])
def delete_application():
    if session.get("role") != "teacher":
        return jsonify({"status": "error", "message": "權限不足"})
    student_id = request.form.get("student_id")
    target_date = request.form.get("target_date")
    
    db = load_data()
    db["applications"] = [
        a for a in db["applications"] 
        if not (a["student_id"] == student_id and a.get("target_date") == target_date)
    ]
    save_data(db)
    return jsonify({"status": "success", "message": "🗑️ 該筆申請資料已成功刪除！"})

# 🎯 新增：一鍵切換鎖定狀態的路由
@app.route("/teacher/toggle_lock", methods=["POST"])
def toggle_lock():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    db = load_data()
    # 反轉目前的鎖定狀態
    db["system_locked"] = not db.get("system_locked", False)
    save_data(db)
    return jsonify({"status": "success", "system_locked": db["system_locked"]})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
