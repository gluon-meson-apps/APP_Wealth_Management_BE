from unittest.mock import MagicMock
import requests
from unified_search_client.unified_search_client import UnifiedSearchClient

class TestUnifiedSearchClient:
    def test_unifiedsearchclient_init_should_have_correct_parameters(self):
        client = UnifiedSearchClient("http://example.com")
        assert client.base_url == "http://example.com"

    def test_unifiedsearchclient_should_send_valid_get_request_to_server(self, mocker):
        # Create an instance of the UnifiedSearchClient class
        client = UnifiedSearchClient("http://example.com")

        # Mock the requests.get function
        mocker.patch("requests.get", return_value=MagicMock())

        # Call the send_request method
        client.send_request("GET", "/health", params={"q": "test"})

        # Assert that requests.get was called with the correct arguments
        requests.get.assert_called_once_with("http://example.com/health", params={"q": "test"})

    def test_unifiedsearchclient_should_send_invalid_post_request_to_server(self, mocker):
        client = UnifiedSearchClient("http://example.com")
        mocker.patch("requests.post", return_value=MagicMock())
        parameters = {
            "files": [
                "file_path_a",
                "file_path_b"
            ],
            "tag": "new_tag"
        }
        client.send_request("POST", "/vector/embedding", params=parameters)
        requests.post.assert_called_once_with("http://example.com/vector/embedding", data=parameters)