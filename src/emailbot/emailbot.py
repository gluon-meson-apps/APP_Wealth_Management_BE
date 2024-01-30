import asyncio
import base64
import logging
import time

import environ
import requests
from dotenv import load_dotenv
from sqlalchemy import text

from action.base import Attachment
from models.email_model.model import Email, EmailAttachment
from third_system.microsoft_graph import Graph
from third_system.unified_search import UnifiedSearch
from utils.utils import extract_json_from_text

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


def handle_response(email, response):
    if response.status_code != 200:
        raise Exception(response.text)
    else:
        chunk = response.content
        chunk_as_string = chunk.decode("utf-8").strip()
        data_as_string = chunk_as_string[len("data:") :] if chunk_as_string.startswith("data:") else ""
        json_result = extract_json_from_text(data_as_string)
        answer = json_result["answer"] if "answer" in json_result and json_result["answer"] else ""
        attachments = (
            [Attachment(**a) for a in json_result["attachment"]]
            if "attachment" in json_result and json_result["attachment"]
            else []
        )
        return answer, attachments


class EmailBot:
    class DatabaseConnection:
        connection_string = ""
        config: EmailBotSettings.EmailDB = None
        engine = None
        connection = None

        def __init__(self, email_db_config: EmailBotSettings.EmailDB):
            self.config = email_db_config

            self.generate_connection_string()

        def generate_connection_string(self):
            if self.config:
                self.connection_string = (
                    f"postgresql+psycopg2://"
                    f"{self.config.USER}:{self.config.PASSWORD}"
                    f"@{self.config.HOST}/{self.config.DATABASE}"
                )

        def connect_database(self):
            import sqlalchemy

            self.engine = sqlalchemy.create_engine(self.connection_string)
            self.connection = self.engine.connect()

        def disconnect_database(self):
            if self.connection:
                self.connection.close()

        def insert_new_email_into_database(self, email: Email):
            sql = f"""INSERT INTO {self.config.DATABASE} VALUES (
    '{email.id}',
    '{email.conversation_id}',
    '{email.subject}',
    '{email.sender.address}',
    '{email.sender.name}',
    '{email.body.content_type}',
    '{email.body.content}',
    {email.has_attachments},
    '\u007b{",".join([url for url in email.attachment_urls])}\u007d',
    '{email.received_date_time}',
    FALSE
)"""
            logging.debug(sql)
            self.connection.execute(text(sql))

        def set_processed_email(self, email):
            self.connection.execute(
                text(f"""
UPDATE {self.config.DATABASE}
SET is_processed = TRUE
WHERE email_id = '{email.id}'
"""
                     )
            )

    def __init__(self, config: EmailBotSettings, graph: Graph, interval=60):
        self.thought_agent_endpoint = config.THOUGHT_AGENT_ENDPOINT
        self.interval = interval
        self.recent_emails = []
        self.database = EmailBot.DatabaseConnection(config.email_db)
        self.graph = graph
        self.unified_search = UnifiedSearch()
        self.database.connect_database()

    def periodically_call_api(self):
        while True:
            self.receive_email()
            self.process_emails()
            time.sleep(self.interval)

    def receive_email(self):
        # todo: currently only use first email to test attachment
        email_list = [self.graph.get_new_emails()[0]]

        for email in email_list:
            email.attachment_urls = self.upload_email_attachments(email)
            self.recent_emails.append(email)
            self.database.insert_new_email_into_database(email)

    def process_emails(self):
        for email in self.recent_emails:
            answer, attachments = self.ask_thought_agent(email)
            self.graph.send_email(email, answer, self.parse_attachments_in_answer(attachments))

            self.database.set_processed_email(email)

    def ask_thought_agent(self, email: Email):
        payload = {
            "question": email.body.content,
            "conversation_id": email.id,
            "user_id": "emailbot",
            "file_urls": email.attachment_urls,
            "from_email": True,
        }
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url=self.thought_agent_endpoint, json=payload, headers=headers)
        return handle_response(email, response)

    def parse_attachments_in_answer(self, attachments: list[Attachment]) -> list[EmailAttachment]:
        result = []
        for a in attachments:
            contents = self.unified_search.download_raw_file_from_minio(a.url) if a.url else None
            if contents:
                result.append(EmailAttachment(name=a.name, bytes=contents, type=a.content_type))
        return result

    def upload_email_attachments(self, email):
        if email.has_attachments:
            attachments = self.graph.list_attachments(email.id)
            files = [
                (
                    "files",
                    (a["name"], base64.b64decode(a["contentBytes"]), a["contentType"]),
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
