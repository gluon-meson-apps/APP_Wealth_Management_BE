import environ
import msal
import requests


@environ.config(prefix="GRAPH_API")
class GraphAPIConfig:
    CLIENT_ID = environ.var("")
    CLIENT_SECRET = environ.var("")
    TENANT_ID = environ.var("")
    USERID = environ.var("")


class Graph:
    settings: GraphAPIConfig

    access_token: str
    app_client: msal.ConfidentialClientApplication

    def __init__(self, config: GraphAPIConfig):
        self.settings = config
        self.create_graph_app_client()
        self.get_access_token()

    def create_graph_app_client(self):
        client_id = self.settings.CLIENT_ID
        tenant_id = self.settings.TENANT_ID
        client_secret = self.settings.CLIENT_SECRET

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app_client = msal.ConfidentialClientApplication(
            client_id=client_id, client_credential=client_secret, authority=authority
        )

    def get_access_token(self):
        scopes = ["https://graph.microsoft.com/.default"]
        result = self.app_client.acquire_token_for_client(scopes=scopes)
        if "access_token" in result:
            self.access_token = result["access_token"]
        else:
            print("获取访问令牌失败")
            raise Exception("Get token failed.")

    def get_new_emails(self):
        endpoint = f"https://graph.microsoft.com/v1.0/users/{self.settings.USERID}/messages?$select=sender,subject,body,hasAttachments&$expand=attachments"
        headers = {"Authorization": "Bearer " + self.access_token}
        response = requests.get(endpoint, headers=headers)
        if response.ok:
            data = response.json()
            return data
        else:
            raise Exception("Getting email failed")

    def list_attachments(self, message_id):
        endpoint = f"https://graph.microsoft.com/v1.0/users/{self.settings.USERID}/messages/{message_id}/attachments"
        headers = {"Authorization": "Bearer " + self.access_token}
        response = requests.get(endpoint, headers=headers)
        if response.ok:
            data = response.json()
            values = data["value"] if "value" in data and data["value"] else []
            return [v for v in values if "contentBytes" in v and v["contentBytes"]]
        else:
            raise Exception("Getting email attachments failed")
