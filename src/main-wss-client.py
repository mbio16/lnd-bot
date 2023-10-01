from logger import Logger
from dotenv import dotenv_values
from lnd_api import LND_api
from lnd_websocket import LND_websocket_client
from db import DB
def main():
    """
    This is the main function that initializes the necessary components and starts the websocket listener.
    
    It first loads the configuration values from the .env file. Then, it initializes the database, logger, 
    LND API, and LND websocket client with the appropriate configuration values.
    
    Finally, it starts the websocket client to listen for HTLC streams.
    """
    
    config = dotenv_values(".env")
    db = DB(
        config["POSTGRES_DATABASE"],
        config["POSTGRES_USER"],
        config["POSTGRES_PASSWORD"],
        config["POSTGRES_HOST"],
        port=int(config["POSTGRES_PORT"]),
    )
    
    logger = Logger(
        config["LOG_FILE"], 
        db, 
        loggin_level=config["LOG_LEVEL"],
        host_name="websocket-client"       
    )
    lnd_api = LND_api(
        config["URL"],
        config["MACAROON"],
        config["CERT_PATH"],
        config["VERIFY_CERT"] == "True",
        logger,
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

    )
    
    
    lnd_websocket.listen_for_htlc_stream()

if __name__ == "__main__":
    main()

