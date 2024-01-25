import json
from unittest.mock import patch

import pytest
from src.emailbot.emailbot import EmailBot


class TestEmailBotContentProcessing:
    def test_email_bot_should_generate_prompt_when_given_an_email(self):
        bot = EmailBot(interval=5)

        email_content = "This is the content of the email"

        bot.read_email(email_content)

class TestEmailBotDatabaseConnection:
    def test_connection_string(self):
        mock_config = {
            'user_name': 'test_user',
            'password': 'test_password',
            'database_url': 'test_url',
            'database_name': 'test_db'
        }

        with patch('builtins.open', return_value=self.mock_open(read_data=json.dumps(mock_config))):
            db_connection = EmailBot.DatabaseConnection('config_file_path.json')

        assert db_connection.connection_string == "postgresql+psycopg2://test_user:test_password@test_url/test_db"

    @patch('sqlalchemy.create_engine')
    def test_connect_database(self, mock_create_engine):
        mock_engine = mock_create_engine.return_value
        mock_connection = mock_engine.connect.return_value

        mock_config = {
            'user_name': 'test_user',
            'password': 'test_password',
            'database_url': 'test_url',
            'database_name': 'test_db'
        }

        with patch('builtins.open', return_value=self.mock_open(read_data=json.dumps(mock_config))):
            db_connection = EmailBot.DatabaseConnection('config_file_path.json')
            db_connection.connect_database()

        assert db_connection.connection is not None
        mock_create_engine.assert_called_once_with('postgresql+psycopg2://test_user:test_password@test_url/test_db')
        mock_engine.connect.assert_called_once()

    def mock_open(self, *args, **kwargs):
        class MockFile:
            def __init__(self, read_data):
                self.read_data = read_data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return self.read_data

        return MockFile(*args, **kwargs)