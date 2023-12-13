import os
import uuid
import requests
import argparse
from tqdm import tqdm


def process_files(directory):
    # 指定文件夹路径
    script_path = './scripts'  # 修改为你的文件夹路径
    log_base_path = './logs'  # 修改为你的文件夹路径

    # 获取文件列表
    file_list = []
    for root, dirs, files in os.walk(script_path):
        if directory and os.path.basename(root) != directory:
            continue

        for file_name in files:
            if file_name.endswith('.txt'):  # 确保只处理文本文件
                file_list.append((root, file_name))

    # 遍历文件列表并处理
    for root, file_name in tqdm(file_list, desc="Processing", unit="file"):
        session_id = str(uuid.uuid4())
        file_path = os.path.join(root, file_name)

        # 获取相对路径，以便创建相应的日志文件夹结构
        relative_path = os.path.relpath(root, script_path)
        log_dir = os.path.join(log_base_path, relative_path)

        # 创建日志文件夹（如果不存在）
        os.makedirs(log_dir, exist_ok=True)

        # 创建保存对话记录的文件
        log_file_path = os.path.join(log_dir, f"{file_name.split('.')[0]}_log.txt")
        with open(file_path, 'r', encoding='utf-8') as file, open(log_file_path, 'w', encoding='utf-8') as log_file:
            lines = file.readlines()
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
                    log_file.write(f"User: {user_input}\n")

                    log_file.write(f"Bot: \n")
                    bot_response_jump_out = response.json()["response"]["jump_out_flag"]
                    if bot_response_jump_out == False:
                        bot_response_messageType = response.json()["response"]["answer"]["messageType"]
                        bot_response_content = response.json()["response"]["answer"]["content"]
                        log_file.write(f"MessageType: {bot_response_messageType}\n")
                        log_file.write(f"Content: {bot_response_content}\n")
                    log_file.write(f"JumpOutFlag: {bot_response_jump_out}\n")

                    log_file.write("-" * 120)
                    log_file.write("\n")
                else:
                    print(f"Error for file {file_name}: {response.status_code}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process files in a directory')
    parser.add_argument('--domain', type=str, help='Specify the directory to process')

    args = parser.parse_args()
    domain = args.domain

    process_files(domain)
