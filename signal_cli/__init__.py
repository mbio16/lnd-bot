from asyncio.log import logger
import json
import requests
from logger import Logger

class Signal_client:
    def __init__(self, source_number: str, recipients: str, url: str,logger:Logger):
        self.number = source_number
        self.recipients = json.loads(recipients)
        self.url = url
        self.logger = logger
    def send_string(self, message: str) -> None:
        data = {
            "message": message,
            "number": self.number,
            "recipients": self.recipients,
        }
        self.logger.info("Preparing to send signal message...")
        self.logger.debug("Data: {}".format(json.dumps(data,indent=1)))
        response = requests.post(self.url, data=json.dumps(data))
        if response.status_code == 200 or response.status_code == 201:
            self.logger.info("Response from signal OK.")
        else:
            self.logger.info("Response from signal FAIL.")
        self.logger.debug("Response code: {} , response data: {}".format(
                response.status_code, 
                json.dumps(response.json(),indent=1)
            ))