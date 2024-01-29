import asyncio
import time

import environ
import requests
from dotenv import load_dotenv
from sqlalchemy import text

from third_system.microsoft_graph import Graph
from third_system.unified_search import UnifiedSearch

load_dotenv()


@environ.config(prefix="EMAIL_BOT")
class EmailBotSettings:
    @environ.config
    class EmailDB:
        HOST = environ.var("")
        USER = environ.var("")
        PASSWORD = environ.var("")
        PORT = environ.var("5432")
        DATABASE = environ.var("")

    email_db = environ.group(EmailDB)
    THOUGHT_AGENT_ENDPOINT = environ.var("http://localhost:7788/score/")


def get_config(cls):
    return environ.to_config(cls)


class EmailBot:
    class DatabaseConnection:
        connection_string = ""
        engine = None
        connection = None

        def __init__(self, email_db_config: EmailBotSettings.EmailDB):
            config = email_db_config

            self.generate_connection_string(config)

        def generate_connection_string(self, config):
            if config:
                self.connection_string = (
                    f"postgresql+psycopg2://{config.USER}:{config.PASSWORD}@{config.HOST}/{config.DATABASE}"
                )

        def connect_database(self):
            import sqlalchemy

            self.engine = sqlalchemy.create_engine(self.connection_string)
            self.connection = self.engine.connect()

        def disconnect_database(self):
            if self.connection:
                self.connection.close()

    def __init__(self, config: EmailBotSettings, graph: Graph, interval=60):
        self.thought_agent_endpoint = config.THOUGHT_AGENT_ENDPOINT
        self.interval = interval
        self.recent_emails = []
        self.database = EmailBot.DatabaseConnection(config.email_db)
        self.graph = graph
        self.unified_search = UnifiedSearch()

    def periodically_call_api(self):
        self.database.connect_database()

        while True:
            if self.check_for_newly_arriving_emails():
                self.receive_email()
                self.process_emails()
            time.sleep(self.interval)

    def check_for_newly_arriving_emails(self):
        # Check if there is any newly arrived email
        data = self.graph.get_new_emails()
        for email in data["value"]:
            print(email["sender"]["emailAddress"]["name"])
            print(email["subject"])
            print(email["bodyPreview"])
            print("-" * 20)
        return True

    def receive_email(self):
        # Pseudo variables
        email_list = ["<EMAIL_A>", "<EMAIL_B>", "<EMAIL_C>"]
        # Call the Graph API, and get the email lists

        # todo: currently only use first email to test attachment
        email_list = [self.graph.get_new_emails()[0]]

        for email in email_list:
            if not self.email_received(email):
                # Call the Graph API to download the email
                email.attachment_urls = self.upload_email_attachments(email)
                self.recent_emails.append(email)
                self.database.connection.execute(
                    text(
                        f"INSERT INTO emails VALUES ({email.conversation_id}, {email.id}, {email.body.content}, 'not_processed')"
                    )
                )

    def email_received(self, email):
        # Check if the email is already received.
        return False

    def process_emails(self):
        for email in self.recent_emails:
            self.ask_thought_agent(email)

            self.database.connection.execute(
                text(f"UPDATE emails SET status = 'processed' WHERE email_id == '{email.id}'")
            )

    def ask_thought_agent(self, email):
        payload = {
            "question": email["body"]["content"],
            "conversation_id": email.id,
            "user_id": "emailbot",
            "file_urls": email.attachment_urls,
        }
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url=self.thought_agent_endpoint, json=payload, headers=headers)
        return self.handle_response(response)

    def extract_content(self, email):
        # pseudo variables
        email_id = "email_id"
        email_content = "email_content"

        return email_id, email_content

    def handle_response(self, response):
        if response.status_code != 200:
            raise Exception(response.text)
        else:
            return response.json()

    def upload_email_attachments(self, email):
        if email.has_attachments:
            attachments = self.graph.list_attachments(email.id)
            files = [
                (
                    "files",
                    (a["name"], a["contentBytes"], a["contentType"]),
                )
                for a in attachments
            ]
            return self.unified_search.upload_file_to_minio(files)
        return []


async def main():
    emailbot_configuration = get_config(EmailBotSettings)
    graph = Graph()
    print(graph.access_token)
    bot = EmailBot(emailbot_configuration, graph)
    bot.periodically_call_api()


if __name__ == "__main__":
    asyncio.run(main())
