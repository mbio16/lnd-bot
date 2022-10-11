from datetime import date
from lnd_api import LND_api
from signal_cli import Signal_client
from db import DB
import locale
from dotenv import dotenv_values
import requests
from logger import Logger

def routing(api:LND_api,db:DB,logger:Logger)->None:
    try:
        time = db.get_youngest_unixtimestamp_routing_tx()
        routing_txs = api.routing_since_time_as_dict(time)
        db.write_tx_to_db(routing_txs, logger)
    except Exception as e:
        logger.error("Routing error: ".format(str(e)))
    

def main():
    config = dotenv_values(".env")

    api = LND_api(
        config["URL"],
        config["MACAROON"],
        config["CERT_PATH"],
        config["VERIFY_CERT"] == "True",
    )
    signal = Signal_client(
        config["SIGNAL_SOURCE_NUMBER"],
        config["SIGNAL_RECIPIENTS"],
        config["SIGNAL_URL"],
    )

    db = DB(
        config["POSTGRES_DATABASE"],
        config["POSTGRES_USER"],
        config["POSTGRES_PASSWORD"],
        config["POSTGRES_HOST"],
    )
    logger = Logger(
        config["LOG_FILE"], 
        db,
        loggin_level=config["LOG_LEVEL"]
    )
    
    #ROUTING
    routing(api,db,logger)
    
        


if __name__ == "__main__":
    main()
