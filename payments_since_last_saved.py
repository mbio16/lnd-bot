from datetime import date
from lnd_api import LND_api
from signal_cli import Signal_client
from db import DB
from logger import Logger
import locale
from dotenv import dotenv_values
import requests
import json


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
    # time = db.get_youngest_unixtimestamp_routing_tx()

    api = LND_api(
        config["URL"],
        config["MACAROON"],
        config["CERT_PATH"],
        config["VERIFY_CERT"] == "True",
        logger,
    )

    index_offset = db.get_last_index_offset()
    routing_txs = api.payments_from_index_offset_as_dict(index_offset)
    db.write_payments_to_db(routing_txs)


if __name__ == "__main__":
    main()
