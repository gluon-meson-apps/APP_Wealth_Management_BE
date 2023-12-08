import unittest
import uuid

import parameterized
import requests

questions_and_expected_responses = [
  [
    '页面看不清楚，请放大50%',
    'enlarge_page',
    [['font_size', '50%', None]]
  ],
  [
    '页面看不清楚，请放大5%',
    'enlarge_page',
    [['font_size', '5%', None]]
  ],

]


class TestIntentAndSlots(unittest.TestCase):

  @parameterized.parameterized.expand(questions_and_expected_responses)
  def test_single_chat_intent_and_slots(self, question, intent, slots):
    random_uuid = uuid.uuid4()
    response = requests.post('http://localhost:7788/chat/', json={
      "user_input": question,
      "session_id": str(random_uuid)
    })

    assert response.status_code == 200
    response_chat = response.json()
    response_chat_intent = response_chat['response']['extra_info']['intent'][
      'name']
    response_chat_slots = response_chat['response']['extra_info']['slot']

    assert response_chat_intent == intent
    assert response_chat_slots == slots


if __name__ == '__main__':
  unittest.main()
