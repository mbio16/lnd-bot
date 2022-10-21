import json
from datetime import date

from matplotlib.font_manager import json_dump
from db import DB
from logger import Logger
import websocket

import ssl

class LND_websocket_client:
    SATS_TO_BTC = 100000000
    MSATS_TO_SATS = 1000
    RESULT = "result"
    EVENT_TYPE = "event_type"
    WIRE_FAILURE = "wire_failure"
    LINK_FAIL_EVENT = "link_fail_event"
    def __init__(self,base_url:str,db: DB, cert_path: str, macaroon: str, logger: Logger) -> None:
        self.base_url = base_url.replace("https","wss")
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.logger = logger
        self.db = db
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}
        self.sslopt = {"ca_cert_path" : self.cert_path}
        websocket.enableTrace(True)
    def __str__(self) -> str:
        return self.base_url
    
    def listen_for_htlc_stream(self):
        
        ws = websocket.WebSocketApp(self.base_url + "/v2/router/htlcevents",
                                header=self.headers,
                                on_open=lambda msg: self.on_open(msg),
                                on_message=lambda ws,msg: self.on_message(ws,msg),
                                on_error=lambda ws,msg: self.on_error(ws,msg),
                                on_close=lambda ws,close_status_code,close_msg: self.on_close(ws, close_status_code,close_msg)
                            )

        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})  
            
    def on_message(self,ws:websocket.WebSocketApp,message:str):
        self.__parse_message(message)
    
    def on_error(self, ws:websocket.WebSocketApp,error:str)->None:
        self.logger.error(str(error))

    def on_close(self,ws:websocket.WebSocketApp, close_status_code:int, close_msg:str)->None:
        self.logger.info("Clossing connection.. {} .. {}".format(str(close_msg),str(close_status_code)))
    def on_open(self,ws:websocket.WebSocketApp)->None:
        self.logger.info("Opening connection to wss...")

    def __parse_message(self,message:str)->None:
        res = json.loads(message)
        res = res[self.RESULT]
        try:
            if res[self.EVENT_TYPE] == "FORWARD" and res[self.LINK_FAIL_EVENT][self.WIRE_FAILURE] == "TEMPORARY_CHANNEL_FAILURE":
                self.logger.info("HTLC fail route message...saving to db")
                self.__failed_htlc_message(res)
                
        except:
            self.logger.info("Not HTLC fail route message... skipping")

    def __failed_htlc_message(self,message:dict)->None:
        res_dict = {
            "chan_in": message["incoming_channel_id"],
            "chan_out": message["outgoing_channel_id"],
            "type":message["event_type"],
            "wire_failure":message["link_fail_event"]["wire_failure"],
            "incoming_amount_msats":int(message["link_fail_event"]["info"]["incoming_amt_msat"]),
            "outgoing_amount_msats":int(message["link_fail_event"]["info"]["outgoing_amt_msat"]),
            "failure_detail":message["link_fail_event"]["failure_detail"]
        }
        #HAS TO BE DONE
            #CHECK IF CHANIDEXISTS
            #SAVEPARAMS INTO DB       
        print(str(res_dict))