from datetime import date
from lnd_api import LND_api
from signal_cli import Signal_client
from db import DB
from logger import Logger
import locale
from dotenv import dotenv_values
import requests


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
    time = db.get_youngest_unixtimestamp_routing_tx()

    api = LND_api(
        config["URL"],
        config["MACAROON"],
        config["CERT_PATH"],
        config["VERIFY_CERT"] == "True",
        logger,
    )
    routing_txs = api.routing_since_time_as_dict(time)
    db.write_tx_to_db(routing_txs, logger)


#     signal = Signal_client(
#         config["SIGNAL_SOURCE_NUMBER"],
#         config["SIGNAL_RECIPIENTS"],
#         config["SIGNAL_URL"],
#     )


#     response, b = api.routing_yesterday()
#     _, a = api.routing_all()
#     text = api.convert_response_routing_to_text(response)
#     message = "Date: " + date.today().strftime("%Y-%m-%d") + "\n"
#     message += "Active channels: " + str(api.get_num_active_channels()) + "\n"
#     message += "Inactive channels: " + str(api.get_num_passive_channels()) + "\n"
#     message += "--------------------------\n"
#     message += "Summary all time:\n"
#     message += "--------------------------\n"
#     message += api.convert_sum_to_text(a) + "\n"
#     message += "--------------------------\n"
#     message += "Summary yersterday:\n"
#     message += "--------------------------\n"
#     message += api.convert_sum_to_text(b) + "\n\n"
#     message += text

#     print(message)
#     content_list = api.routing_yesterday_get_all_as_dict()
#     db.write_tx_to_db(content_list)
#     signal.send_string(message)


if __name__ == "__main__":
    main()
