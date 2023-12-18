import unittest
import os
import uuid
from tqdm import tqdm

from parameterized import parameterized
import requests

from action.base import ResponseMessageType


def process_files(directory) -> []:
    # 指定文件夹路径
    script_path = './scripts'  # 修改为你的文件夹路径

    # 获取文件列表
    file_list = []
    for root, dirs, files in os.walk(script_path):
        if directory and os.path.basename(root) != directory:
            continue

        for file_name in files:
            if file_name.endswith('.txt'):  # 确保只处理文本文件
                file_list.append((root, file_name))
    all_responses = []

    # 遍历文件列表并处理
    for root, file_name in tqdm(file_list, desc="Processing", unit="file"):
        file_path = os.path.join(root, file_name)
        # 获取对应expect file path
        expect_path = (file_path
                       .replace("scripts", "expects"))
        session_id = str(uuid.uuid4())
        responses = []

        if os.path.exists(expect_path):
            with open(file_path, 'r', encoding='utf-8') as file, open(expect_path, 'r',
                                                                      encoding='utf-8') as expect_file:
                lines = file.readlines()
                expect_lines = expect_file.readlines()
                for i in range(len(lines)):
                    user_input = lines[i].strip()
                    response = {
                        "session_id": session_id,
                        "question": user_input,
                        "expect_file_path": expect_path,
                        "flag": expect_lines[7 * i + 0].strip()[13:] == 'True',
                        "content": {
                            'message_type': expect_lines[7 * i + 1].strip()[13:],
                            'operate_type': expect_lines[7 * i + 2].strip()[13:],
                            'category': expect_lines[7 * i + 3].strip()[10:],
                            'valueType': expect_lines[7 * i + 4].strip()[11:],
                            'value': expect_lines[7 * i + 5].strip()[7:]
                        }
                    }
                    responses.append(response)
            all_responses.append(responses)
    return all_responses


questions_and_expected_responses = process_files("")


class TestIntentAndSlots(unittest.TestCase):

    @parameterized.expand(questions_and_expected_responses)
    def test_single_chat_intent_and_slots(self, *expects):
        print("\n")
        print(expects[0]["expect_file_path"])
        for expect in expects:
            response = requests.post('http://localhost:7788/chat/', json={
                "user_input": expect["question"],
                "session_id": expect["session_id"]
            })

            assert response.status_code == 200
            response_chat = response.json()

            response_jump_out_flag = response_chat['response']['jump_out_flag']
            assert expect['flag'] == response_jump_out_flag

            if not expect['flag']:
                response_message_type = response_chat['response']['answer']['messageType']
                assert response_message_type == expect['content']['message_type']

                if expect['content']['message_type'] == ResponseMessageType.FORMAT_INTELLIGENT_EXEC:
                    response_action_operate_type = response_chat['response']['answer']['content']['operateType']
                    response_action_operate_slots_value = \
                        response_chat['response']['answer']['content']['operateSlots'][
                            'value']
                    assert response_action_operate_type == expect['content']['operate_type']
                    assert response_action_operate_slots_value == expect['content']['value']

                    if expect['content']['operate_type'] in ['PAGE_RESIZE_INCREMENT', 'PAGE_RESIZE_TARGET',
                                                             'ADJUST_HEADER']:
                        response_action_operate_slots_category = \
                            response_chat['response']['answer']['content']['operateSlots'][
                                'category']
                        assert response_action_operate_slots_category == expect['content']['category']

                    if expect['content']['operate_type'] in ['ADJUST_HEADER']:
                        response_action_operate_slots_category = \
                            response_chat['response']['answer']['content']['operateSlots'][
                                'valueType']
                        assert response_action_operate_slots_category == expect['content']['valueType']
            else:
                assert response_chat['response']['answer'] == {}
                print("No")



if __name__ == '__main__':
    unittest.main()
