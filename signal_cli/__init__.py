import json
import requests


class Signal_client:
    def __init__(self, source_number: str, recipients: str, url: str):
        self.number = source_number
        self.recipients = json.loads(recipients)
        self.url = url

    def send_string(self, message: str) -> None:
        data = {
            "message": message,
            "number": self.number,
            "recipients": self.recipients,
        }
        print(str(data))
        response = requests.post(self.url, data=json.dumps(data))
        print(str(response))
