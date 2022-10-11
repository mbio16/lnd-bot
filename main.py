from lnd_api import LND_api
from signal_cli import Signal_client
from db import DB
from dotenv import dotenv_values
from logger import Logger
from message_creator import Message_creator


def routing(api: LND_api, db: DB, logger: Logger) -> None:
    try:
        time = db.get_youngest_unixtimestamp_routing_tx()
        routing_txs = api.routing_since_time_as_dict(time)
        db.write_tx_to_db(routing_txs, logger)
    except Exception as e:
        logger.error("Routing error: {}".format(str(e)))


def channel_backup(api: LND_api, db: DB, logger: Logger) -> None:
    try:
        res = api.channel_backup_as_dict()
        db.write_channel_backup(res, logger)
    except Exception as e:
        logger.error("Channel backups error: {}".format(str(e)))


def invoices(api: LND_api, db: DB, logger: Logger) -> None:
    try:
        min_offset = db.delete_all_invoices_that_are_open(logger)
        res = api.invoices_since_last_offset_as_list(min_offset)
        db.write_invoices(res, logger)
    except Exception as e:
        logger.error("Invoices error: {}".format(str(e)))


def payments(api: LND_api, db: DB, logger: Logger) -> None:
    try:
        index_offset = db.get_last_index_offset()
        routing_txs = api.payments_from_index_offset_as_dict(index_offset)
        db.write_payments_to_db(routing_txs)
    except Exception as e:
        logger.error("Payments error: {}".format(str(e)))


def balance(api: LND_api, db: DB, logger: Logger) -> None:
    try:
        res = api.balance_as_dict()
        db.write_balance(res)
    except Exception as e:
        logger.error("Balance error: {}".format(str(e)))


def main():
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
    signal_client = Signal_client(
        config["SIGNAL_SOURCE_NUMBER"],
        config["SIGNAL_RECIPIENTS"],
        config["SIGNAL_URL"],
    )

    message_creator = Message_creator(db, api, logger)
    # ROUTING
    routing(api, db, logger)

    # CHANNEL BACKUP ERROR
    channel_backup(api, db, logger)

    # INVOICES
    invoices(api, db, logger)

    # BALANCE
    balance(api, db, logger)

    # SEND SIGNAL MESSAGE
    signal_client.send_string(str(message_creator))


if __name__ == "__main__":
    main()
