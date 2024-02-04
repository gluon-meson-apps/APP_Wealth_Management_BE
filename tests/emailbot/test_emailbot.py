import json
from unittest.mock import patch

import environ

from src.emailbot.emailbot import EmailBot, EmailBotSettings


class TestEmailBotContentProcessing:
    @patch("src.third_system.microsoft_graph.Graph")
    def test_email_bot_should_generate_prompt_when_given_an_email(self, mock_graph):
        mock_config = environ.to_config(
            EmailBotSettings,
            environ={
                "APP_EMAIL_DB_USER": "test_user",
                "APP_EMAIL_DB_PASSWORD": "test_password",
                "APP_EMAIL_DB_HOST": "test_url",
                "APP_EMAIL_DB_DATABASE": "test_db",
                "APP_THOUGHT_AGENT_ENDPOINT": "test_endpoint"
            }
        )
        bot = EmailBot(config=mock_config, graph=mock_graph, interval=5)

        email_content = "This is the content of the email"

        assert True


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
        with db_connection.engine.connect() as connection:
            assert connection is not None
            mock_engine.connect.assert_called_once()

        assert db_connection.engine is not None
        mock_create_engine.assert_called_once_with("postgresql+psycopg2://test_user:test_password@test_url/test_db", pool_pre_ping=True)
