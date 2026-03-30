import os
import json
import requests
from datetime import datetime, timedelta
import subprocess

# 1. 配置信息
REPO_DIR = "/Users/yourname/health_sync" # 你的本地 Git 仓库路径
DATA_FILE = os.path.join(REPO_DIR, 'health_data.json')
WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=你的TOKEN"

def generate_and_send_report():
    # 2. 拉取最新代码
    print("Pulling latest data from Git...")
    subprocess.run(f"cd {REPO_DIR} && git pull origin master", shell=True)

    # 3. 计算昨天的日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 4. 读取数据
    if not os.path.exists(DATA_FILE):
        print("未找到数据文件")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if yesterday not in data:
        print(f"没有找到 {yesterday} 的数据记录")
        return

    record = data[yesterday]
    
    # 提取各项数据
    steps = int(record.get('step', 0))
    static = int(record.get('static', 0))
    active = int(record.get('active', 0))
    intake = int(record.get('intake', 0))
    
    total_burn = static + active
    
    # 5. 组装钉钉消息（包含状态判断）
    if intake > 0:
        deficit = total_burn - intake
        intake_str = f"{intake} 千卡"
        if deficit > 0:
            conclusion = f"🎉 制造了 {deficit} 千卡的热量缺口，非常棒！"
        else:
            conclusion = f"⚠️ 热量盈余 {abs(deficit)} 千卡，今天要管住嘴啦！"
    else:
        intake_str = "未填写 📝"
        conclusion = "💡 记得去网页端补填昨天的饮食摄入哦！"

    text_content = f"""📊 昨日 ({yesterday}) 健康总结
-------------------------
🏃‍♂️ 步数：{steps} 步
🔥 总消耗：{total_burn} 千卡 
   (静息 {static} + 活动 {active})
🍔 总摄入：{intake_str}
-------------------------
{conclusion}"""

    # 6. 发送钉钉 Webhook
    payload = {
        "msgtype": "text",
        "text": {
            "content": text_content # 确保内容包含钉钉机器人安全关键字（如"健康"或"总结"）
        }
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print("钉钉发送状态:", response.text)

if __name__ == '__main__':
    generate_and_send_report()