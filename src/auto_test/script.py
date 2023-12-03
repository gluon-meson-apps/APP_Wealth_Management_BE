import os
import uuid
import requests

# 初始化会话ID
session_id = str(uuid.uuid4())

# 指定文件夹路径
script_path = './scripts'  # 修改为你的文件夹路径
log_path = './logs'  # 修改为你的文件夹路径

# 获取文件夹中所有文件
files = os.listdir(script_path)

# 遍历文件夹中的每个文件
for file_name in files:
    if file_name.endswith('.txt'):  # 确保只处理文本文件
        file_path = os.path.join(script_path, file_name)

        # 打开文件进行读取
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # 创建保存对话记录的文件
        log_file_path = os.path.join(log_path, f"{file_name.split('.')[0]}_log.txt")
        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            for line in lines:
                user_input = line.strip()

                # 发送请求给聊天机器人
                payload = {
                    "user_input": user_input,
                    "session_id": session_id
                }

                response = requests.post('http://localhost:7788/chat/', json=payload)

                # 解析并记录机器人的响应
                if response.status_code == 200:
                    bot_response = response.json()["response"]["text"]
                    log_file.write(f"User: {user_input}\nBot: {bot_response}\n")
                    log_file.write("-" * 120)
                    log_file.write("\n")
                else:
                    print(f"Error for file {file_name}: {response.status_code}")
