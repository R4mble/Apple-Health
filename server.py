from flask import Flask, request, jsonify, render_template, redirect
import json
import os
import subprocess
from datetime import datetime

app = Flask(__name__)

# 配置路径
REPO_DIR = 'data'  # 替换为你的实际路径
DATA_FILE = os.path.join(REPO_DIR, 'health_data.json')

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_and_push(data, commit_msg):
    # 1. 保存到 JSON
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 2. 推送到 Git
    git_command = f'cd {REPO_DIR} && git add health_data.json && git commit -m "{commit_msg}" && git push origin master'
    subprocess.run(git_command, shell=True)


def _ensure_day(data, date):
    if date not in data:
        data[date] = {}
    return data[date]


def _recompute_intake_from_food_log(day):
    items = day.get('food_log') or []
    if not items:
        return
    total = sum(float(x.get('kcal', 0) or 0) for x in items)
    day['intake'] = total

# 路由 1：前端可视化页面
@app.route('/', methods=['GET'])
def index():
    data = load_data()
    return render_template('index.html', records=data)

# 路由 2：追加一条饮食（吃了啥 + 热量），并同步总摄入 intake
@app.route('/api/food', methods=['POST'])
def add_food():
    date = request.form.get('date')
    item = (request.form.get('item') or '').strip()
    try:
        kcal = float(request.form.get('kcal', 0) or 0)
    except ValueError:
        kcal = 0.0

    if not date or not item or kcal <= 0:
        return redirect('/')

    data = load_data()
    day = _ensure_day(data, date)
    food_log = day.get('food_log')
    if not isinstance(food_log, list):
        food_log = []
    food_log.append({'item': item, 'kcal': kcal})
    day['food_log'] = food_log
    _recompute_intake_from_food_log(day)

    save_and_push(data, f"Web: Add food for {date}")
    return redirect('/')


# 路由 2b：追加一条运动记录
@app.route('/api/exercise', methods=['POST'])
def add_exercise():
    date = request.form.get('date')
    name = (request.form.get('name') or '').strip()
    if not date or not name:
        return redirect('/')

    entry = {'name': name}
    dm = request.form.get('duration_min')
    if dm is not None and str(dm).strip() != '':
        try:
            entry['duration_min'] = int(float(dm))
        except ValueError:
            pass
    ek = request.form.get('kcal')
    if ek is not None and str(ek).strip() != '':
        try:
            entry['kcal'] = float(ek)
        except ValueError:
            pass

    data = load_data()
    day = _ensure_day(data, date)
    ex_log = day.get('exercise_log')
    if not isinstance(ex_log, list):
        ex_log = []
    ex_log.append(entry)
    day['exercise_log'] = ex_log

    save_and_push(data, f"Web: Add exercise for {date}")
    return redirect('/')


# 路由 2c：保存当日心得
@app.route('/api/note', methods=['POST'])
def save_note():
    date = request.form.get('date')
    note = (request.form.get('note') or '').strip()
    if not date:
        return redirect('/')

    data = load_data()
    day = _ensure_day(data, date)
    if note:
        day['daily_note'] = note
    else:
        day.pop('daily_note', None)

    save_and_push(data, f"Web: Update note for {date}")
    return redirect('/')

# 路由 3：接收 iOS 快捷指令发来的体征数据
@app.route('/api/health', methods=['POST'])
def sync_health():
    req_data = request.get_json()
    today = datetime.now().strftime('%Y-%m-%d')
    
    data = load_data()
    if today not in data:
        data[today] = {}
        
    # 更新当天数据 (保留可能已经填写的 intake)
    data[today]['static'] = float(req_data.get('static', 0))
    data[today]['active'] = float(req_data.get('active', 0))
    data[today]['step'] = float(req_data.get('step', 0))
    data[today]['distance'] = float(req_data.get('distance', 0))
    
    save_and_push(data, f"iOS: Auto sync health data for {today}")
    return jsonify({"code": 200, "message": "Success", "date": today})

if __name__ == '__main__':
    # 请确保已经在 NAS 环境中安装了 flask: pip3 install flask
    app.run(host='0.0.0.0', port=5221)