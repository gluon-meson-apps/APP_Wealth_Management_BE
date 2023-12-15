import unittest
import uuid

from parameterized import parameterized
import requests

from action.base import ResponseMessageType

questions_and_expected_responses = [
    [
        '页面看不清楚，请放大50%',
        False,
        {
            'message_type': 'FORMAT_INTELLIGENT_EXEC',
            'operate_type': 'PAGE_RESIZE_INCREMENT',
            'category': 'INCREASE',
            'value': '50'
        }
    ],
    [
        '页面看不清楚，请放大5%',
        False,
        {
            'message_type': 'FORMAT_INTELLIGENT_EXEC',
            'operate_type': 'PAGE_RESIZE_INCREMENT',
            'category': 'INCREASE',
            'value': '0'
        }
    ],
    [
        '天气真好',
        True,
        {
        }
    ],
    [
        '开通新功能',
        False,
        {
            'message_type': ResponseMessageType.FORMAT_TEXT
        }
    ],

]


class TestIntentAndSlots(unittest.TestCase):

    @parameterized.expand(questions_and_expected_responses)
    def test_single_chat_intent_and_slots(self, question, jump_out_flag, content):
        random_uuid = uuid.uuid4()
        response = requests.post('http://localhost:7788/chat/', json={
            "user_input": question,
            "session_id": str(random_uuid)
        })

        assert response.status_code == 200
        response_chat = response.json()

        response_jump_out_flag = response_chat['response']['jump_out_flag']
        assert jump_out_flag == response_jump_out_flag

        if not jump_out_flag:
            response_message_type = response_chat['response']['answer']['messageType']
            assert content['message_type'] == response_message_type

            if content['message_type'] == ResponseMessageType.FORMAT_INTELLIGENT_EXEC:
                response_action_operate_type = response_chat['response']['answer']['content']['operateType']
                response_action_operate_slots_value = response_chat['response']['answer']['content']['operateSlots'][
                    'value']
                assert content['operate_type'] == response_action_operate_type
                assert content['value'] == response_action_operate_slots_value

                if content['operate_type'] in ['PAGE_RESIZE_INCREMENT', 'PAGE_RESIZE_TARGET', 'ADJUST_HEADER']:
                    response_action_operate_slots_category = \
                        response_chat['response']['answer']['content']['operateSlots'][
                            'category']
                    assert content['category'] == response_action_operate_slots_category

                if content['operate_type'] in ['ADJUST_HEADER']:
                    response_action_operate_slots_category = \
                        response_chat['response']['answer']['content']['operateSlots'][
                            'valueType']
                    assert content['valueType'] == response_action_operate_slots_category


if __name__ == '__main__':
    unittest.main()
