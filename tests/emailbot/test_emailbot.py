import json
from unittest.mock import patch

import environ

from src.emailbot.emailbot import EmailBot, EmailBotSettings


class TestEmailBotContentProcessing:
    def test_email_bot_should_generate_prompt_when_given_an_email(self):
        mock_config = environ.to_config(
            EmailBotSettings.EmailDB,
            environ={
                "APP_USER": "test_user",
                "APP_PASSWORD": "test_password",
                "APP_HOST": "test_url",
                "APP_DATABASE": "test_db"
            }
        )
        bot = EmailBot(email_db_config=mock_config, interval=5)

        email_content = "This is the content of the email"

        bot.read_email(email_content)


class TestEmailBotDatabaseConnection:
    def test_connection_string(self):
        mock_config = environ.to_config(
            EmailBotSettings.EmailDB,
            environ={
                "APP_USER": "test_user",
                "APP_PASSWORD": "test_password",
                "APP_HOST": "test_url",
                "APP_DATABASE": "test_db"
            }
        )

        db_connection = EmailBot.DatabaseConnection(mock_config)

        assert db_connection.connection_string == "postgresql+psycopg2://test_user:test_password@test_url/test_db"

    @patch("sqlalchemy.create_engine")
    def test_connect_database(self, mock_create_engine):
        mock_engine = mock_create_engine.return_value

        mock_config = environ.to_config(
            EmailBotSettings.EmailDB,
            environ={
                "APP_USER": "test_user",
                "APP_PASSWORD": "test_password",
                "APP_HOST": "test_url",
                "APP_DATABASE": "test_db"
            }
        )

        db_connection = EmailBot.DatabaseConnection(mock_config)
        db_connection.connect_database()

        assert db_connection.connection is not None
        mock_create_engine.assert_called_once_with("postgresql+psycopg2://test_user:test_password@test_url/test_db")
        mock_engine.connect.assert_called_once()
