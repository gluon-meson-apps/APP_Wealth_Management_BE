from unittest.mock import MagicMock

from intent import get_intent_examples
from unified_search_client.unified_search_client import UnifiedSearchClient


class TestIntents:
    def test_get_intent_examples_should_generate_the_list_of_examples(self, mocker):
        mocker.patch.object(UnifiedSearchClient, "send_request")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '[{"meta__score":109.81185150146484,"id":"9c821a4d-eb1b-45b9-93b2-7732ddfc94bd","text":"{\\"intent\\":\\"others\\",\\"example\\":\\"this is an example\\"}","meta__reference": {"meta__source_type":"txt","meta__source_name":"temp_unified_search_roving.txt","meta__page_number":0}}]'

        UnifiedSearchClient.send_request.return_value = mock_response

        user_input = "What is your name?"
        result = get_intent_examples(user_input)
        expected_result = [{
            "example": "this is an example",
            "intent": "others",
            "score": 109.81185150146484
        }]
        assert result == expected_result


