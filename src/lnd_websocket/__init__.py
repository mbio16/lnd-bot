import json
from datetime import date

from matplotlib.font_manager import json_dump
from db import DB
from logger import Logger
from lnd_api import LND_api
import websocket
from datetime import datetime
import ssl

class LND_websocket_client:
    SATS_TO_BTC = 100000000
    MSATS_TO_SATS = 1000
    RESULT = "result"
    EVENT_TYPE = "event_type"
    WIRE_FAILURE = "wire_failure"
    LINK_FAIL_EVENT = "link_fail_event"
    def __init__(self,base_url:str,db: DB, cert_path: str, macaroon: str, lnd_api:LND_api,logger: Logger) -> None:
        self.base_url = base_url.replace("https","wss")
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.logger = logger
        self.db = db
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}
        self.sslopt = {"ca_cert_path" : self.cert_path}
        self.lnd_api = lnd_api
        websocket.enableTrace(True)
    def __str__(self) -> str:
        return self.base_url
    
    def listen_for_htlc_stream(self):
        
        ws = websocket.WebSocketApp(self.base_url + "/v2/router/htlcevents",
                                header=self.headers,
                                on_open=lambda msg: self.__on_open(msg),
                                on_message=lambda ws,msg: self.__on_message(ws,msg),
                                on_error=lambda ws,msg: self.__on_error(ws,msg),
                                on_close=lambda ws,close_status_code,close_msg: self.__on_close(ws, close_status_code,close_msg)
                            )

        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})  
            
    def __on_message(self,ws:websocket.WebSocketApp,message:str):
        self.__parse_message(message)
    
    def __on_error(self, ws:websocket.WebSocketApp,error:str)->None:
        self.logger.error(str(error))

    def __on_close(self,ws:websocket.WebSocketApp, close_status_code:int, close_msg:str)->None:
        self.logger.info("Clossing connection.. {} .. {}".format(str(close_msg),str(close_status_code)))
    def __on_open(self,ws:websocket.WebSocketApp)->None:
        self.logger.info("Opening connection to wss...")

    def __parse_message(self,message:str)->None:
        res = json.loads(message)
        res = res[self.RESULT]
        #try:
        if res[self.EVENT_TYPE] == "FORWARD" and res[self.LINK_FAIL_EVENT][self.WIRE_FAILURE] == "TEMPORARY_CHANNEL_FAILURE":
                self.logger.info("HTLC fail route message...saving to db")
                self.__failed_htlc_message(res)
                
        #except Exception as ex:
           # self.logger.info("Not HTLC fail route message... skipping")
        #    self.logger.error(str(ex))

    def __failed_htlc_message(self,message:dict)->None:
        time = int(int(message["timestamp_ns"])/(1000000000))
        print(str(time))
        res_dict = {
            "chan_in": int(message["incoming_channel_id"]),
            "chan_out": int(message["outgoing_channel_id"]),
            "event_type":message["event_type"],
            "wire_failure":message["link_fail_event"]["wire_failure"],
            "incoming_amount_msats":int(message["link_fail_event"]["info"]["incoming_amt_msat"]),
            "outgoing_amount_msats":int(message["link_fail_event"]["info"]["outgoing_amt_msat"]),
            "failure_detail":message["link_fail_event"]["failure_detail"],
            "time":datetime.fromtimestamp(time)
        }
        #HAS TO BE DONE
        self.__channel_in_db(res_dict["chan_in"])
        self.__channel_in_db(res_dict["chan_out"])
            #SAVEPARAMS INTO DB       
        self.db.write_failed_htlc(res_dict)
    
    def __channel_in_db(self,channel_id:int)->None:
        if not self.db.is_channel_in_db(channel_id):
            response = self.lnd_api.get_nodes_in_channel(str(channel_id))
            alias = response[0]
            remote_pub_key = response[2]
            self.db.check_channel_in_db(channel_id,remote_pub_key,alias,self.logger)