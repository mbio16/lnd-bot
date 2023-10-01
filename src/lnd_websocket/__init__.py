import json
from datetime import date

from db import DB
from logger import Logger
from lnd_api import LND_api
from message_creator import Message_creator
from signal_cli import Signal_client
import websocket
from datetime import datetime
import os
import ssl


class LND_websocket_client:
    """
    This class represents the LND websocket client.
    It establishes a websocket connection to the LND API and listens for HTLC events.
    The events are then processed and handled accordingly.
    """

    SATS_TO_BTC = 100000000
    MSATS_TO_SATS = 1000
    RESULT = "result"
    EVENT_TYPE = "event_type"
    WIRE_FAILURE = "wire_failure"
    LINK_FAIL_EVENT = "link_fail_event"
    EVENT_FORWARD_EVENT = "forward_event"
    INFO = "info"
    FORWARD_VALUE = "FORWARD"
    TEMPORARY_CHANNEL_FAILURE = "TEMPORARY_CHANNEL_FAILURE"

    def __init__(
        self,
        base_url: str,
        db: DB,
        cert_path: str,
        macaroon: str,
        lnd_api: LND_api,
        logger: Logger,
        verify_cert: bool,
        send_routing_message: bool,
        signal_client: Signal_client | None = None,
        message_creator: Message_creator | None = None,
    ) -> None:
        """
        Initialize the LND_websocket_client.

        Parameters:
        base_url (str): The base URL for the websocket connection.
        db (DB): The database object to interact with the database.
        cert_path (str): The path to the SSL certificate.
        macaroon (str): The macaroon for authentication.
        lnd_api (LND_api): The LND API object to interact with the LND API.
        logger (Logger): The logger object to log messages.
        verify_cert (bool): Whether to verify the SSL certificate or not.
        send_routing_message (bool): Whether to send routing messages or not.
        signal_client (Signal_client): The Signal client object to send messages. Default is None.
        message_creator (Message_creator): The message creator object to create messages. Default is None.

        Returns:
        None
        """

        self.base_url = base_url.replace("https", "wss")
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.logger = logger
        self.db = db
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}
        self.lnd_api = lnd_api
        self.ssl_context = None
        self.send_routing_message = send_routing_message
        self.verify_cert = verify_cert
        self.message_creator = message_creator
        self.signal_client = signal_client
        self.ssl_opt = self.__setup_ssl_context()
        websocket.enableTrace(True)

    def __str__(self) -> str:
        return self.base_url

    def __setup_ssl_context(self) -> dict:
        """
        Sets up the SSL context for the websocket connection.

        This function sets up the SSL context based on the provided certificate path and whether the certificate needs to be verified.
        It also sets the environment variables REQUESTS_CA_BUNDLE and SSL_CERT_FILE with the certificate path.

        Returns:
        dict: A dictionary with the SSL options for the websocket connection.
        """

        os.environ["REQUESTS_CA_BUNDLE"] = self.cert_path
        os.environ["SSL_CERT_FILE"] = self.cert_path
        if self.verify_cert:
            return {"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": self.cert_path}
        else:
            return {"cert_reqs": ssl.CERT_NONE}

    def listen_for_htlc_stream(self):
        """
        This function listens for HTLC (Hashed TimeLock Contract) events from the LND (Lightning Network Daemon) API.
        It establishes a websocket connection to the LND API and listens for HTLC events.
        The events are then processed and handled accordingly.

        Returns:
        None
        """

        ws = websocket.WebSocketApp(
            self.base_url + "/v2/router/htlcevents",
            header=self.headers,
            on_open=lambda msg: self.__on_open(msg),
            on_message=lambda ws, msg: self.__on_message(ws, msg),
            on_error=lambda ws, msg: self.__on_error(ws, msg),
            on_close=lambda ws, close_status_code, close_msg: self.__on_close(
                ws, close_status_code, close_msg
            ),
        )
        self.logger.debug(
            "ssl context: verify cert {}, context {}".format(
                str(self.verify_cert), str(self.ssl_opt)
            )
        )
        ws.run_forever(sslopt=self.ssl_opt)

    def __on_message(self, ws: websocket.WebSocketApp, message: str):
        """
        Handles incoming messages from the websocket connection.

        This function is called when a message is received from the websocket connection.
        It parses the message and processes it accordingly.

        Parameters:
        ws (websocket.WebSocketApp): The websocket connection object.
        message (str): The received message.

        Returns:
        None
        """

        self.__parse_message(message)

    def __on_error(self, ws: websocket.WebSocketApp, error: str) -> None:
        """
        Handles any errors that occur during the websocket connection.

        This function is called when an error occurs in the websocket connection.
        It logs the error message for debugging and troubleshooting purposes.

        Parameters:
        ws (websocket.WebSocketApp): The websocket connection object.
        error (str): The error message.

        Returns:
        None
        """

        self.logger.error(str(error))

    def __on_close(
        self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str
    ) -> None:
        """
        Handles the closing of the websocket connection.

        This function is called when the websocket connection is closed.
        It logs the closing message and status code for debugging and troubleshooting purposes.

        Parameters:
        ws (websocket.WebSocketApp): The websocket connection object.
        close_status_code (int): The status code of the closing connection.
        close_msg (str): The closing message.

        Returns:
        None
        """

        self.logger.info(
            "Clossing connection.. {} .. {}".format(
                str(close_msg), str(close_status_code)
            )
        )

    def __on_open(self, ws: websocket.WebSocketApp) -> None:
        """
        Handles the opening of the websocket connection.

        This function is called when the websocket connection is opened.
        It logs a message indicating that the connection has been opened.

        Parameters:
        ws (websocket.WebSocketApp): The websocket connection object.

        Returns:
        None
        """
        self.logger.info("Opening connection to wss...")

    def __parse_message(self, message: str) -> None:
        """
        Parses the incoming message from the websocket connection.

        This function is called when a message is received from the websocket connection.
        It parses the message and processes it accordingly.

        Parameters:
        message (str): The received message.

        Returns:
        None
        """
        res = json.loads(message)
        res = res[self.RESULT]
        self.logger.debug("Original message: {}".format(str(res)))
        self.__check_if_fail_route_message(res)
        self.__check_if_routing_message(res)
        self.__check_if_routing_preimage_message(res)

    def __check_if_fail_route_message(self, res: dict) -> None:
        """
        Checks if the received message is a fail route message.

        This function is called to check if the received message is a fail route message.
        If it is, it saves the message to the database.

        Parameters:
        res (dict): The received message.

        Returns:
        None
        """
        try:
            if (
                res[self.EVENT_TYPE] == self.FORWARD_VALUE
                and res[self.LINK_FAIL_EVENT][self.WIRE_FAILURE]
                == self.TEMPORARY_CHANNEL_FAILURE
            ):
                self.logger.info("HTLC fail route message...saving to db")
                self.__failed_htlc_message(res)
        except Exception as ex:
            self.logger.info("Not HTLC fail route message... skipping")
            self.logger.debug("Error message: {}".format(str(ex)))

    def __check_if_routing_message(self, res: dict) -> None:
        """
        Checks if the received message is a routing message.

        This function is called to check if the received message is a routing message.
        If it is, it processes the message accordingly.

        Parameters:
        res (dict): The received message.

        Returns:
        None
        """
        try:
            if res[self.EVENT_TYPE] == self.FORWARD_VALUE and (
                "info" in res["forward_event"]
            ):
                self.logger.info("Forward event...")
                self.__check_good_forward(res)
        except Exception as ex:
            self.logger.info("NOT Forward event...... skipping")
            self.logger.debug("Error message: {}".format(str(ex)))

    def __check_if_routing_preimage_message(self, res: dict):
        """
        Checks if the received message is a routing preimage message.

        This function is called to check if the received message is a routing preimage message.
        If it is, it processes the message accordingly.

        Parameters:
        res (dict): The received message.

        Returns:
        None
        """
        try:
            if res[self.EVENT_TYPE] == self.FORWARD_VALUE and (
                "preimage" in res["settle_event"]
            ):
                self.logger.info("Forward setteling...")
                self.__check_good_settling(res)
        except Exception as ex:
            self.logger.info("NOT Forward setteling...... skipping")
            self.logger.debug("Error message: {}".format(str(ex)))

    def __failed_htlc_message(self, message: dict) -> None:
        """
        Processes the failed HTLC message.

        This function is called to process the failed HTLC message.
        It extracts relevant information from the message and saves it to the database.

        Parameters:
        message (dict): The failed HTLC message.

        Returns:
        None
        """
        time = int(int(message["timestamp_ns"]) / (1000000000))
        res_dict = {
            "chan_in": int(message["incoming_channel_id"]),
            "chan_out": int(message["outgoing_channel_id"]),
            "event_type": message["event_type"],
            "wire_failure": message["link_fail_event"]["wire_failure"],
            "incoming_amount_msats": int(
                message["link_fail_event"]["info"]["incoming_amt_msat"]
            ),
            "outgoing_amount_msats": int(
                message["link_fail_event"]["info"]["outgoing_amt_msat"]
            ),
            "failure_detail": message["link_fail_event"]["failure_detail"],
            "time": datetime.fromtimestamp(time),
        }
        self.__channel_in_db(res_dict["chan_in"])
        self.__channel_in_db(res_dict["chan_out"])
        self.db.write_failed_htlc(res_dict)

    def __check_good_forward(self, message: dict) -> None:
        """
        Checks if the received message is a good forward event.

        This function is called to check if the received message is a good forward event.
        If it is, it extracts relevant information from the message and saves it to the database.

        Parameters:
        message (dict): The received message.

        Returns:
        None
        """
        incoming_amt_msat = int(message["forward_event"]["info"]["incoming_amt_msat"])
        outgoing_amt_msat = int(message["forward_event"]["info"]["outgoing_amt_msat"])
        routing_fee_msat = incoming_amt_msat - outgoing_amt_msat
        routing_fee_sats = (
            routing_fee_msat / self.MSATS_TO_SATS
        )  # Convert msats to sats
        incoming_amt_sats = (
            incoming_amt_msat / self.MSATS_TO_SATS
        )  # Convert incoming msats to sats
        outgoing_amt_sats = (
            outgoing_amt_msat / self.MSATS_TO_SATS
        )  # Convert outgoing msats to sats
        incoming_htlc_id = int(message["incoming_htlc_id"])
        outgoing_htlc_id = int(message["outgoing_htlc_id"])

        incoming_channel_id = int(message["incoming_channel_id"])
        outgoing_channel_id = int(message["outgoing_channel_id"])
        self.__channel_in_db(incoming_channel_id)
        self.__channel_in_db(outgoing_channel_id)

        self.logger.info(
            "Routing fee in sats: {}, Incoming amount in sats: {}, Outgoing amount in sats: {}, Incoming HTLC ID: {}, Outgoing HTLC ID: {}, Incoming Channel ID: {}, Outgoing Channel ID: {}".format(
                routing_fee_sats,
                incoming_amt_sats,
                outgoing_amt_sats,
                incoming_htlc_id,
                outgoing_htlc_id,
                incoming_channel_id,
                outgoing_channel_id,
            )
        )
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
            outgoing_channel_id=outgoing_channel_id,
        )

    def __check_good_settling(self, message: dict) -> None:
        """
        Checks if the received message is a good settling event.

        This function is called to check if the received message is a good settling event.
        If it is, it extracts relevant information from the message and saves it to the database.

        Parameters:
        message (dict): The received message.

        Returns:
        None
        """
        incoming_channel_id = int(message["incoming_channel_id"])
        outgoing_channel_id = int(message["outgoing_channel_id"])
        incoming_htlc_id = int(message["incoming_htlc_id"])
        outgoing_htlc_id = int(message["outgoing_htlc_id"])
        self.logger.info(
            "Incoming Channel ID: {}, Outgoing Channel ID: {}, Incoming HTLC ID: {}, Outgoing HTLC ID: {}".format(
                incoming_channel_id,
                outgoing_channel_id,
                incoming_htlc_id,
                outgoing_htlc_id,
            )
        )
        self.db.save_settled_routing(
            incoming_channel_id=incoming_channel_id,
            outgoing_channel_id=outgoing_channel_id,
            incoming_htlc_id=incoming_htlc_id,
            outgoing_htlc_id=outgoing_htlc_id,
        )
        if self.send_routing_message:
            self.logger.info("Sending routing info to singal client")
            response_dict = self.db.get_htlc_routing_confirmed(
                incoming_htlc_id=incoming_htlc_id,
                outgoing_htlc_id=outgoing_htlc_id,
                incoming_channel_id=incoming_channel_id,
                outgoing_channel_id=outgoing_channel_id,
            )
            self.logger.debug("DB response: {}".format(str(response_dict)))
            text_response = self.message_creator.reouting_htlc(response_dict)
            self.signal_client.send_string(text_response)

    def __channel_in_db(self, channel_id: int) -> None:
        """
        Checks if the channel is already in the database.

        This function is called to check if the channel with the given channel ID is already present in the database.
        If it is not, it retrieves the nodes in the channel from the LND API and saves the channel information to the database.

        Parameters:
        channel_id (int): The channel ID to check.

        Returns:
        None
        """

        if not self.db.is_channel_in_db(channel_id):
            response = self.lnd_api.get_nodes_in_channel(str(channel_id))
            alias = response[0]
            remote_pub_key = response[2]
            self.db.check_channel_in_db(channel_id, remote_pub_key, alias, self.logger)
