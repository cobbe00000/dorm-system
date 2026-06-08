from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import datetime
import time
from datetime import datetime as dt
from playwright.sync_api import sync_playwright  # 🎯 載入你最厲害的自動化套件

app = Flask(__name__)
app.secret_key = "dorm_system_secret_key_2026"

# 🎯 實體專案目錄路徑
BASE_DIR = "c:\\DormSystem"
DB_FILE = os.path.join(BASE_DIR, "data.json")

TEACHER_PWD = "0800092000"

# 🎯 學校自動化登入的真實帳密（直接綁定你提供的值）
SCHOOL_USER = "1020901"
SCHOOL_PWD = "Aaaa0800092000"

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

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

# =================================================================
# 🛠️ 【Playwright 核心自動化邏輯工具函式】
# =================================================================
def get_chinese_weekday(date_str):
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[date_obj.weekday()]

def auto_determine_class(student_id):
    try:
        sid = int(student_id)
    except ValueError:
        return None
    if sid == 387023:
        current_month = datetime.datetime.now().month
        if current_month in [1, 2, 6, 7, 8, 12]:
            return "餐飲二5"
        elif current_month in [3, 4, 5, 9, 10, 11]:
            return "餐飲二6"
    if 387001 <= sid <= 387027:
        return "餐飲二5"
    elif 387029 <= sid <= 387054:
        return "餐飲二6"
    return None

# =================================================================
# 🛣️ 【路由控制區】
# =================================================================

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
        
        return jsonify({"status": "success", "message": f"📥 {target_date} 的資料填報成功！"})

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

@app.route("/teacher/toggle_lock", methods=["POST"])
def toggle_lock():
    if session.get("role") != "teacher":
        return jsonify({"status": "error"})
    db = load_data()
    db["system_locked"] = not db.get("system_locked", False)
    save_data(db)
    return jsonify({"status": "success", "system_locked": db["system_locked"]})


# =================================================================
# 🚀 【核心合體：一鍵驅動 Playwright 自動化登記學校網站】
# =================================================================
@app.route("/teacher/submit_to_school", methods=["POST"])
def submit_to_school():
    if session.get("role") != "teacher":
        return jsonify({"status": "error", "message": "權限不足"})
    
    payload = request.get_json()
    monday_date = payload.get("monday")
    weekly_data = payload.get("data")  # 接收前端大總表算好並打包好的全班週數據
    
    success_count = 0
    fail_count = 0
    error_details = []

    try:
        with sync_playwright() as p:
            # 這裡為了整合進網頁後端，保持 headless=False 可以讓你在伺服器端親眼看見它跑
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 對話視窗處理
            def handle_dialog(dialog):
                print(f"\n🌐 學校網頁系統提示：[{dialog.message}]")
                try:
                    dialog.accept()
                except Exception:
                    pass
            page.on("dialog", handle_dialog)
            
            print("🚀 [自動化開始] 正在開啟學校宿舍管理網頁...")
            page.goto("https://www.csic.khc.edu.tw/aspx/dormSystem/login.aspx")
            
            # 1. 輸入真實綁定的學校帳密
            print("正在自動填入學校帳號密碼...")
            page.fill("input[name='ctl00$ContentPlaceHolderMaster$TextBox_ID']", SCHOOL_USER)
            page.fill("input[name='ctl00$ContentPlaceHolderMaster$TextBox_Password']", SCHOOL_PWD)
            time.sleep(0.1)
            
            # 2. 切換身分為教師
            print("正在切換身分為『教師』...")
            try:
                page.click("input[id*='RadioButton_Teacher']")
            except Exception:
                try:
                    page.click("text=教師")
                except Exception:
                    pass
            time.sleep(0.1)
            
            # 3. 點擊登入
            print("正在點擊『登入』...")
            page.click("input[name='ctl00$ContentPlaceHolderMaster$Button_Login']")
            page.wait_for_load_state("networkidle")
            
            # 4. 點擊進入填報頁面
            print("正在進入『教師填報請假』系統面...")
            if page.locator("a:has-text('教師填報請假')").count() > 0:
                page.click("a:has-text('教師填報請假')")
            else:
                page.click("text=教師填報請假")
            page.wait_for_load_state("networkidle")

            # 5. 🎯 核心大洗牌：遍歷前端打包送來的每位學生、每週 7 天的所有狀態
            for student in weekly_data:
                student_id = student['student_id']
                student_name = student['student_name']
                weekly_status = student['weekly_status'] # 格式：{"2026-06-08": "工讀(免早點,要晚點)", ...}
                
                # 自動判斷班級
                target_class = auto_determine_class(student_id)
                if not target_class:
                    print(f"⚠️ 學號 {student_id}({student_name}) 無法辨識班級，跳過。")
                    fail_count += 1
                    continue
                
                # 遍歷週一到週日這 7 天
                for date_str, status in weekly_status.items():
                    # 💡 【高能優化】：如果狀態是預設的 "留宿"，學校網站不用特別填寫，直接跳過加快速度！
                    if status == "留宿" or "未設定" in status:
                        continue
                        
                    target_weekday = get_chinese_weekday(date_str)
                    student_row_id = None
                    loop_count = 0
                    
                    print(f"\n🤖 處理進度：學號 {student_id} ({student_name}) | 日期：{date_str} ({target_weekday}) -> 欲填入狀態：{status}")
                    
                    # 進入你的死纏爛打重新整理與肉搜機制
                    while True:
                        loop_count += 1
                        if target_class == "餐飲二5":
                            if loop_count > 1:
                                try:
                                    page.click("text=餐飲二5")
                                    page.wait_for_timeout(1500)
                                except: pass
                        elif target_class == "餐飲二6":
                            try:
                                class_radio = page.locator(f"input[type='radio'][id*='{target_class}']")
                                if class_radio.count() == 0:
                                    class_radio = page.locator(f"//input[@type='radio'][following-sibling::label[contains(text(), '{target_class}')]]")
                                if class_radio.count() > 0:
                                    class_radio.first.click()
                                    class_radio.first.dispatch_event("click")
                                else:
                                    page.locator(f"text={target_class}").first.click()
                                    page.locator(f"text={target_class}").first.dispatch_event("click")
                                page.wait_for_timeout(3000) # 給予緩衝時間載入
                                page.wait_for_load_state("networkidle")
                            except Exception:
                                pass

                        # 地毯式分頁搜尋
                        max_page_attempts = 4
                        for current_page_idx in range(1, max_page_attempts + 1):
                            rows = page.locator("table#ctl00_ContentPlaceHolderMaster_gvData tr").all()
                            for row in rows:
                                row_text = row.inner_text()
                                if student_id in row_text:
                                    select_element = row.locator(f"select[id$='_{target_weekday}']").first
                                    if select_element.count() > 0:
                                        student_row_id = select_element.get_attribute("id")
                                        break
                            if student_row_id:
                                break
                            
                            # 翻頁
                            next_page_str = str(current_page_idx + 1)
                            next_page_btn = page.locator(f"table#ctl00_ContentPlaceHolderMaster_gvData a:has-text('{next_page_str}')").first
                            if next_page_btn.count() == 0:
                                next_page_btn = page.locator(f"a:has-text('{next_page_str}')").first
                            if next_page_btn.count() > 0:
                                try:
                                    next_page_btn.click()
                                    page.wait_for_timeout(1500)
                                    page.wait_for_load_state("networkidle")
                                except Exception:
                                    break
                            else:
                                break
                        
                        if student_row_id or loop_count >= 2: # 最多嘗試 2 輪避免卡死
                            break
                        else:
                            time.sleep(1)

                    # 真正進行網頁欄位填值與儲存
                    if student_row_id:
                        try:
                            page.select_option(f"select[id='{student_row_id}']", value=status)
                            page.locator(f"select[id='{student_row_id}']").dispatch_event("change")
                            time.sleep(1.5) # 確保網頁後台鎖定
                            
                            # 點擊儲存
                            if page.locator("input[value='儲存']").count() > 0:
                                page.click("input[value='儲存']")
                            elif page.locator("button:has-text('儲存')").count() > 0:
                                page.click("button:has-text('儲存')")
                            else:
                                page.click("text=儲存")
                            
                            page.wait_for_timeout(1500)
                            page.wait_for_load_state("networkidle")
                            success_count += 1
                            print(f"✅ 成功幫學生 {student_name}({student_id}) 登記並存檔完成！")
                        except Exception as inner_e:
                            fail_count += 1
                            error_details.append(f"{student_id} 填寫出錯: {str(inner_e)}")
                    else:
                        print(f"❌ 遍歷分頁完畢，依然在學校名單上找不到學號 {student_id}")
                        fail_count += 1

            print("\n🏁 [自動化登記全部結束] 關閉學校瀏覽器中...")
            browser.close()

        return jsonify({
            "status": "success",
            "message": f"🎉 學校網站登記任務執行完畢！\n\n主動過濾並成功寫入登記：{success_count} 筆。\n無法寫入或失敗：{fail_count} 筆。"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"💥 自動化連線在登入或初始化階段遭遇嚴重錯誤：{str(e)}"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
