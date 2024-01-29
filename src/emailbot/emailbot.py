import asyncio
import time
from base64 import b64decode

import environ
import requests
from sqlalchemy import text
from third_system.microsoft_graph import Graph, GraphAPIConfig


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
                self.connection_string = f"postgresql+psycopg2://{config.USER}:{config.PASSWORD}@{config.HOST}/{config.DATABASE}"

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

            if email["hasAttachments"]:
                for attachment in email["attachments"]:
                    full_file_name = attachment["name"]
                    content_bytes = attachment["contentBytes"]
                    with open(full_file_name, "wb") as f:
                        decoded_content = b64decode(content_bytes)
                        f.write(decoded_content)
                    print(f"保存附件 {full_file_name} 到 {full_file_name}")
                print("-" * 20)
        return True

    def receive_email(self):
        # Pseudo variables
        email_list = ["<EMAIL_A>", "<EMAIL_B>", "<EMAIL_C>"]
        # Call the Graph API, and get the email lists

        for email in email_list:
            if not self.email_received(email):
                # Call the Graph API to download the email
                self.recent_emails.append(email)
                self.database.connection.execute(
                    text(
                        f"INSERT INTO emails VALUES ({email.conversation_id}, {email.id}, {email.content}, 'not_processed')")
                )

    def email_received(self, email):
        # Check if the email is already received.
        return False

    def process_emails(self):
        for email in self.recent_emails:
            email_id, email_content = self.extract_content(email)
            result = self.ask_thought_agent(email_id, email_content)

            self.database.connection.execute(
                text(f"UPDATE emails SET status = 'processed' WHERE email_id == '{email_id}'")
            )

    def ask_thought_agent(self, email_id, email_content):
        payload = {
            "question": email_content,
            "conversation_id": email_id,
            "user_id": "emailbot"
        }
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(
            url=self.thought_agent_endpoint,
            json=payload,
            headers=headers
        )
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


async def main():
    emailbot_configuration = get_config(EmailBotSettings)
    graph_api_configuration = get_config(GraphAPIConfig)
    graph = Graph(graph_api_configuration)
    token = await graph.get_access_token()
    print(token)
    bot = EmailBot(emailbot_configuration, graph)
    await bot.periodically_call_api()


if __name__ == "__main__":
    asyncio.run(main())
