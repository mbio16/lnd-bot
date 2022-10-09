from datetime import date
from lnd_api import LND_api
from signal_cli import Signal_client
from db import DB
from logger import Logger
import locale
from dotenv import dotenv_values
from message_creator import Message_creator



def main():
    locale.setlocale(locale.LC_ALL, "")
    config = dotenv_values(".env")
    db = DB(
        config["POSTGRES_DATABASE"],
        config["POSTGRES_USER"],
        config["POSTGRES_PASSWORD"],
        config["POSTGRES_HOST"],
    )
    logger = Logger(config["LOG_FILE"], db, loggin_level=config["LOG_LEVEL"])

    api = LND_api(
        config["URL"],
        config["MACAROON"],
        config["CERT_PATH"],
        config["VERIFY_CERT"] == "True",
        logger,
    )
    message = Message_creator(db,api,logger)
    print(message.routing_all())
    print(message.fee_all())

if __name__ == "__main__":
    main()