import asyncio
import base64
import json
import time
from typing import Generator

import aiohttp
import environ
from dotenv import load_dotenv
from gluon_meson_sdk.client.sse_client import AsyncSSEClient
from gluon_meson_sdk.models.chat_model import AioResponseCapture
from loguru import logger
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


def handle_response(json_result):
    answer = json_result["answer"] if "answer" in json_result and json_result["answer"] else ""
    attachments_dict = extract_json_from_text(json_result["attachment"]) if "attachment" in json_result else None
    attachment = Attachment(**attachments_dict) if attachments_dict else None
    return answer, [attachment] if attachment else []


def format_html_content(content):
    return content.replace("'", "&apos;")


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

        def insert_processed_email_into_database(self, email: Email):
            sql = f"""INSERT INTO emails VALUES (
    '{email.id}',
    '{email.conversation_id}',
    '{email.subject}',
    '{email.sender.address}',
    '{email.sender.name}',
    '{email.body.content_type}',
    '{format_html_content(email.body.content)}',
    {email.has_attachments},
    '\u007b{",".join([url for url in email.attachment_urls])}\u007d',
    '{email.received_date_time}',
    TRUE
)"""
            print(sql)
            self.connection.execute(text(sql))
            self.connection.commit()

        def set_processed_email(self, email):
            self.connection.execute(
                text(
                    f"""
UPDATE emails
SET is_processed = TRUE
WHERE id = '{email.id}'
"""
                )
            )
            self.connection.commit()

    def __init__(self, config: EmailBotSettings, graph: Graph, interval=300):
        self.thought_agent_endpoint = config.THOUGHT_AGENT_ENDPOINT
        self.interval = interval
        self.database = EmailBot.DatabaseConnection(config.email_db)
        self.graph = graph
        self.unified_search = UnifiedSearch()
        self.database.connect_database()

    async def periodically_call_api(self):
        while True:
            new_email = await self.receive_email()
            await self.process_emails(new_email)
            time.sleep(self.interval)

    async def receive_email(self):
        new_email = await self.graph.get_first_inbox_message()
        if new_email:
            new_email.attachment_urls = await self.upload_email_attachments(new_email)
        return new_email

    async def process_emails(self, new_email):
        if new_email:
            answer, attachments = await self.ask_thought_agent(new_email)
            await self.graph.send_email(new_email, answer, await self.parse_attachments_in_answer(attachments))
            self.database.set_processed_email(new_email)

    async def _ask_thought_agent(self, payload: dict) -> Generator[str, list[EmailAttachment], None]:
        streaming_returned = False
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.thought_agent_endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                    },
                ) as resp:
                    response = resp.content.iter_chunks()
                    response_capture = AioResponseCapture(response)
                    client = AsyncSSEClient(response_capture)
                    async for event in client.events():
                        streaming_returned = True
                        yield handle_response(extract_json_from_text(event.data))
            except Exception as err:
                logger.error("Error with thought agent:", err)
                yield "", []

        if not streaming_returned and response_capture.collected_response:
            response_json = json.loads(response_capture.collected_response)
            yield handle_response(response_json)

    async def ask_thought_agent(self, email: Email) -> (str, list[EmailAttachment]):
        payload = {
            "question": email.body.content,
            "conversation_id": email.id,
            "user_id": "emailbot",
            "file_urls": email.attachment_urls,
            "from_email": True,
        }
        answers = ""
        attachments = []
        async for i_answer, i_attachments in self._ask_thought_agent(payload):
            answers += i_answer
            attachments += i_attachments

        return answers, attachments

    async def parse_attachments_in_answer(self, attachments: list[Attachment]) -> list[EmailAttachment]:
        result = []
        for a in attachments:
            contents = await self.unified_search.download_raw_file_from_minio(a.url) if a.url else None
            if contents:
                result.append(EmailAttachment(name=a.name, bytes=base64.b64encode(contents), type=a.content_type))
        return result

    async def upload_email_attachments(self, email):
        if email.has_attachments:
            attachments = await self.graph.list_attachments(email.id)
            files = [
                (
                    "files",
                    (a["name"], base64.b64decode(a["contentBytes"]), a["contentType"]),
                )
                for a in attachments
            ]
            return await self.unified_search.aupload_file_to_minio(files)
        return []


async def main():
    emailbot_configuration = get_config(EmailBotSettings)
    graph = await Graph()
    bot = EmailBot(emailbot_configuration, graph)
    await bot.periodically_call_api()


if __name__ == "__main__":
    asyncio.run(main())
