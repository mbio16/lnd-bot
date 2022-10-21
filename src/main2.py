from logger import Logger
from dotenv import dotenv_values
from lnd_websocket import LND_websocket_client
from db import DB
def main():
    
    
    config = dotenv_values(".env")
    db = DB(
        config["POSTGRES_DATABASE"],
        config["POSTGRES_USER"],
        config["POSTGRES_PASSWORD"],
        config["POSTGRES_HOST"],
        port=int(config["POSTGRES_PORT"]),
    )
    logger = Logger(config["LOG_FILE"], db, loggin_level=config["LOG_LEVEL"])
    lnd_websocket = LND_websocket_client(
        config["URL"],
        db,
        config["CERT_PATH"],
        config["MACAROON"],
        logger   
    )
    print(str(lnd_websocket))
    
    lnd_websocket.test()

if __name__ == "__main__":
    main()

