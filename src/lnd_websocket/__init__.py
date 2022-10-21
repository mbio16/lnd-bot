import json
from datetime import date
from db import DB
from logger import Logger
import websocket

import ssl

class LND_websocket_client:
    SATS_TO_BTC = 100000000
    MSATS_TO_SATS = 1000
    def __init__(self,base_url:str,db: DB, cert_path: str, macaroon: str, logger: Logger) -> None:
        self.base_url = base_url.replace("https","wss")
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.logger = logger
        self.db = db
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}
        self.sslopt = {"ca_cert_path" : self.cert_path}
    def __str__(self) -> str:
        return self.base_url
    
    def run_htlc_error(self):
        websocket.enableTrace(True)

        ws = websocket.WebSocketApp(self.base_url + "/v2/router/htlcevents",
                                header=self.headers,
                                on_open=lambda msg: self.on_open(msg),
                                on_message=lambda ws,msg: self.on_message(ws,msg),
                                on_error=lambda ws,msg: self.on_error(ws,msg),
                                on_close=lambda ws,close_status_code,close_msg: self.on_close(ws, close_status_code,close_msg)
                            )

        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection  
            
    def on_message(self,ws,message):
        print(str(message))

    def on_error(self, ws,error):
        print(error)

    def on_close(self,ws, close_status_code, close_msg):
        self.logger.info("Clossing connection..{}".format(str(close_msg)))
    def on_open(self,ws):
        print("Opened connection")


