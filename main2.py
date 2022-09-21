from datetime import date
from lnd_api import LND_api
from signal_cli import Signal_client
from db import DB
import locale
from dotenv import dotenv_values
import requests


def main():
    locale.setlocale(locale.LC_ALL, "")
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
    content_list = api.routing_yesterday_get_all_as_dict()
    db.write_tx_to_db(content_list)


if __name__ == "__main__":
    main()
