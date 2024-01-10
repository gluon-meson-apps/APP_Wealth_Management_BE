import requests


class HsbcConnectApi:
    def __init__(self):
        self.base_url = "https://hkl20146575.hc.cloud.hk.hsbc:25000/PaymentRulesValidator/Report"

    def validate_file(self, file) -> str:
        if file:
            response = requests.post(self.base_url, files={"Attachment": file}, verify=False)
            return response.text
        raise FileNotFoundError("No file valid.")
