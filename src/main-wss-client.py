from logger import Logger
from dotenv import dotenv_values
from lnd_api import LND_api
from lnd_websocket import LND_websocket_client
from signal_cli import Signal_client
from message_creator import Message_creator
from db import DB
def main():
    """
    This is the main function. It initializes the necessary components and starts the websocket listener.
    
    The function now loads the configuration values from the .env file. Following this, it sets up the database, logger, 
    LND API, and LND websocket client using the loaded configuration values.
    
    The final step is to start the websocket client to listen for HTLC streams.
    """
    
    config = dotenv_values(".env")
    
    db = DB(
        db=config["POSTGRES_DATABASE"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
        host=config["POSTGRES_HOST"],
        port=int(config["POSTGRES_PORT"]),
    )
    
    logger = Logger(
        file_url=config["LOG_FILE"], 
        db=db, 
        loggin_level=config["LOG_LEVEL"],
        host_name="websocket-client"       
    )
    
    if config["SEND_ROUTING_NOTIFICATION"] == "True":
        signal_client = Signal_client(
            source_number=config["SIGNAL_SOURCE_NUMBER"],
            recipients=config["SIGNAL_RECIPIENTS"],
            base_url=config["SIGNAL_BASE_URL"],
            logger=logger,
        )
    else:
        signal_client = None
    
    lnd_api = LND_api(
        base_url=config["URL"],
        macaroon=config["MACAROON"],
        cert_path=config["CERT_PATH"],
        verify_cert=config["VERIFY_CERT"] == "True",
        logger=logger,
    )
    
    message_creator = Message_creator(
        db=db,
        lnd_api=lnd_api,
        logger=logger,
    )
    
    lnd_websocket = LND_websocket_client(
        base_url=config["URL"],
        db=db,
        cert_path=config["CERT_PATH"],
        macaroon=config["MACAROON"],
        verify_cert=config["VERIFY_CERT"] == "True",
        send_routing_message=config["SEND_ROUTING_NOTIFICATION"] == "True",
        lnd_api=lnd_api,
        logger=logger,
        signal_client=signal_client,
        message_creator=message_creator,
    )
    
    
    lnd_websocket.listen_for_htlc_stream()

if __name__ == "__main__":
    main()

