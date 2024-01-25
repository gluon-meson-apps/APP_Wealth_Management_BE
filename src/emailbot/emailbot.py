import json
import time

import requests
from sqlalchemy import text


class EmailBot:
    class DatabaseConnection:
        connection_string = ""
        engine = None
        connection = None

        def __init__(self, config_file_path):
            with open(config_file_path) as config_file:
                config = json.load(config_file)

            self.generate_connection_string(config)

        def generate_connection_string(self, config):
            if config:
                self.connection_string = f"postgresql+psycopg2://{config['user_name']}:{config['password']}@{config['database_url']}/{config['database_name']}"

        def connect_database(self):
            import sqlalchemy
            self.engine = sqlalchemy.create_engine(self.connection_string)
            self.connection = self.engine.connect()


    def __init__(self, interval=60):
        self.gluon_meson_endpoint = "http://localhost:7788/score/"
        self.interval = interval
        self.recent_emails = []
        self.database = EmailBot.DatabaseConnection("emailbot_db.json")

    def periodically_call_api(self):
        while True:
            if self.check_for_newly_arriving_emails():
                self.receive_email()
                self.process_emails()
            time.sleep(self.interval)

    def check_for_newly_arriving_emails(self):
        # Check if there is any newly arrived email
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
                    text(f"INSERT INTO emails VALUES ({email.conversation_id}, {email.id}, {email.content}, 'not_processed')")
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
            url=self.gluon_meson_endpoint,
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


if __name__ == "__main__":
    bot = EmailBot()
    bot.periodically_call_api()
