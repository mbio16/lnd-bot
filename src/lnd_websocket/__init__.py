import json
from datetime import date

from db import DB
from logger import Logger
from lnd_api import LND_api
from message_creator import Message_creator
import websocket
from datetime import datetime
import os
import ssl
class LND_websocket_client:
    SATS_TO_BTC = 100000000
    MSATS_TO_SATS = 1000
    RESULT = "result"
    EVENT_TYPE = "event_type"
    WIRE_FAILURE = "wire_failure"
    LINK_FAIL_EVENT = "link_fail_event"
    EVENT_FORWARD_EVENT="forward_event"
    INFO="info"
    FORWARD_VALUE="FORWARD"
    TEMPORARY_CHANNEL_FAILURE="TEMPORARY_CHANNEL_FAILURE"
    def __init__(self,base_url:str,db: DB, cert_path: str, macaroon: str, lnd_api:LND_api,logger: Logger,verify_cert:bool,send_routing_message:bool) -> None:
        self.base_url = base_url.replace("https","wss")
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.logger = logger
        self.db = db
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}
        self.lnd_api = lnd_api
        self.ssl_context = None
        self.send_routing_message = send_routing_message
        self.verify_cert = verify_cert
        self.message_creator=Message_creator(db=self.db,logger=self.logger,lnd_api=self.lnd_api)
        self.ssl_opt = self.__setup_ssl_context()
        websocket.enableTrace(True)

    def __str__(self) -> str:
        return self.base_url
    
    def __setup_ssl_context(self)->dict:
        os.environ["REQUESTS_CA_BUNDLE"] = self.cert_path
        os.environ["SSL_CERT_FILE"] = self.cert_path
        if self.verify_cert:
            return {
                        "cert_reqs": ssl.CERT_REQUIRED,
                        "ca_certs": self.cert_path
                    }
        else:
            return {"cert_reqs": ssl.CERT_NONE}        
    def listen_for_htlc_stream(self):
        
        ws = websocket.WebSocketApp(
                                self.base_url + "/v2/router/htlcevents",
                                header=self.headers,
                                on_open=lambda msg: self.__on_open(msg),
                                on_message=lambda ws,msg: self.__on_message(ws,msg),
                                on_error=lambda ws,msg: self.__on_error(ws,msg),
                                on_close=lambda ws,close_status_code,close_msg: self.__on_close(ws, close_status_code,close_msg)
                            )
        self.logger.debug("ssl context: verify cert {}, context {}".format(str(self.verify_cert),str(self.ssl_opt)))
        ws.run_forever(sslopt=self.ssl_opt)
        
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
        self.logger.debug("Original message: {}".format(str(res)))  
        self.__check_if_fail_route_message(res)
        self.__check_if_routing_message(res)
        self.__check_if_routing_preimage_message(res)
    def __check_if_fail_route_message(self,res:dict)->None:
        try:
            if res[self.EVENT_TYPE] == self.FORWARD_VALUE and res[self.LINK_FAIL_EVENT][self.WIRE_FAILURE] == self.TEMPORARY_CHANNEL_FAILURE:
                self.logger.info("HTLC fail route message...saving to db")
                self.__failed_htlc_message(res)
        except Exception as ex:
           self.logger.info("Not HTLC fail route message... skipping")
           self.logger.debug("Error message: {}".format(str(ex)))
    
    def __check_if_routing_message(self,res:dict)->None:
        try:
            if res[self.EVENT_TYPE] == self.FORWARD_VALUE and ("info" in res["forward_event"]):
                self.logger.info("Forward event...")
                self.__check_good_forward(res)
        except Exception as ex:
           self.logger.info("NOT Forward event...... skipping")
           self.logger.debug("Error message: {}".format(str(ex))) 
    def __check_if_routing_preimage_message(self,res:dict):
        try:
            if res[self.EVENT_TYPE] == self.FORWARD_VALUE and ("preimage" in res["settle_event"]):
                self.logger.info("Forward setteling...")
                self.__check_good_settling(res)
        except Exception as ex:
           self.logger.info("NOT Forward setteling...... skipping")
           self.logger.debug("Error message: {}".format(str(ex)))      
    
    def __failed_htlc_message(self,message:dict)->None:
        time = int(int(message["timestamp_ns"])/(1000000000))
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
        self.__channel_in_db(res_dict["chan_in"])
        self.__channel_in_db(res_dict["chan_out"])     
        self.db.write_failed_htlc(res_dict)
        
    def __check_good_forward(self,message:dict)->None:
        incoming_amt_msat = int(message["forward_event"]["info"]["incoming_amt_msat"])
        outgoing_amt_msat = int(message["forward_event"]["info"]["outgoing_amt_msat"])
        routing_fee_msat = incoming_amt_msat - outgoing_amt_msat
        routing_fee_sats = routing_fee_msat / self.MSATS_TO_SATS  # Convert msats to sats
        incoming_amt_sats = incoming_amt_msat / self.MSATS_TO_SATS  # Convert incoming msats to sats
        outgoing_amt_sats = outgoing_amt_msat / self.MSATS_TO_SATS  # Convert outgoing msats to sats
        incoming_htlc_id = int(message["incoming_htlc_id"])
        outgoing_htlc_id = int(message["outgoing_htlc_id"])
        
        incoming_channel_id = int(message["incoming_channel_id"])
        outgoing_channel_id = int(message["outgoing_channel_id"])
        self.__channel_in_db(incoming_channel_id)
        self.__channel_in_db(outgoing_channel_id)
        
        self.logger.info("Routing fee in sats: {}, Incoming amount in sats: {}, Outgoing amount in sats: {}, Incoming HTLC ID: {}, Outgoing HTLC ID: {}, Incoming Channel ID: {}, Outgoing Channel ID: {}".format(routing_fee_sats, incoming_amt_sats, outgoing_amt_sats, incoming_htlc_id, outgoing_htlc_id, incoming_channel_id, outgoing_channel_id))
        self.db.save_forward_values_to_db(
            incoming_amt_msat=incoming_amt_msat,
            outgoing_amt_msat=outgoing_amt_msat,
            routing_fee_msat=routing_fee_msat,
            routing_fee_sats=routing_fee_sats,
            incoming_amt_sats=incoming_amt_sats,
            outgoing_amt_sats=outgoing_amt_sats,
            incoming_htlc_id=incoming_htlc_id,
            outgoing_htlc_id=outgoing_htlc_id,
            incoming_channel_id=incoming_channel_id,
            outgoing_channel_id=outgoing_channel_id
        )
    def __check_good_settling(self,message:dict)->None:
        incoming_channel_id = int(message['incoming_channel_id'])
        outgoing_channel_id = int(message['outgoing_channel_id'])
        incoming_htlc_id = int(message['incoming_htlc_id'])
        outgoing_htlc_id = int(message['outgoing_htlc_id'])
        self.logger.info("Incoming Channel ID: {}, Outgoing Channel ID: {}, Incoming HTLC ID: {}, Outgoing HTLC ID: {}".format(incoming_channel_id, outgoing_channel_id, incoming_htlc_id, outgoing_htlc_id))
        self.db.save_settled_routing(
            incoming_channel_id=incoming_channel_id,
            outgoing_channel_id=outgoing_channel_id,
            incoming_htlc_id=incoming_htlc_id,
            outgoing_htlc_id=outgoing_htlc_id
        )
        if self.send_routing_message:
            pass
            
        


        
        
    
    def __channel_in_db(self,channel_id:int)->None:
        if not self.db.is_channel_in_db(channel_id):
            response = self.lnd_api.get_nodes_in_channel(str(channel_id))
            alias = response[0]
            remote_pub_key = response[2]
            self.db.check_channel_in_db(channel_id,remote_pub_key,alias,self.logger)