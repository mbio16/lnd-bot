from db import DB
from logger import Logger
from lnd_api import LND_api
from datetime import date


class Message_creator:
    def __init__(self, db: DB, lnd_api: LND_api, logger: Logger) -> None:
        self.db = db
        self.logger = logger
        self.lnd_api = lnd_api

    def __date_str(self) -> str:
        return "Date: \t{}\n".format(date.today().strftime("%Y-%m-%d"))

    def __active_channels(self) -> str:
        return "Active channels: \t{}\n".format(self.lnd_api.get_num_active_channels())

    def __inactive_channels(self) -> str:
        return "Inactive channels: \t{}\n".format(
            str(self.lnd_api.get_num_passive_channels())
        )

    def __channel_alias(self) -> str:
        return "Alias: \t{}\n".format(str(self.lnd_api))

    def __routing_all(self) -> str:
        value = self.__btc_format(self.db.get_sum_routing_all())
        return "Routing [BTC]: \t{}\n".format(value)

    def __fee_all(self) -> str:
        value = self.__sats_format(self.db.get_fee_routing_all_sats())
        return "Fee [sats]: \t{}\n".format(value)

    def __routing_yesterday(self) -> str:
        value = self.__btc_format(self.db.get_sum_routing_yesterday())
        return "Routing [BTC]: \t{}\n".format(value)

    def __fee_yesterday(self) -> str:
        value = self.__sats_format(self.db.get_fee_yesterday_sats())
        return "Fee [sats]: \t{}\n".format(value)

    def __count_routing_tx_all(self) -> str:
        value = self.__sats_format(self.db.get_tx_routing_count_all())
        print(value)
        return "TXs: \t\t\t{}\n".format(value)

    def __count_routing_tx_yesterday(self) -> str:
        value = self.__sats_format(self.db.get_tx_routing_count_yesterday())
        return "TX: \t\t\t\n".format(value)

    def balance(self) -> str:
        res = self.db.get_balance()
        message = "Date: \t\t{} \n".format(res["date"])
        message += "Inbound: \t{} \n".format(self.__sats_format(res["inbound"]))
        message += "Outbound: \t{} \n".format(self.__sats_format(res["outbound"]))
        message += "Onchain: \t{} \n".format(self.__sats_format(res["onchain"]))
        message += "Pending: \t{} \n".format(self.__sats_format(res["pending"]))
        message += self.__line()
        return message

    def routing_events(self) -> str:
        res = self.db.get_routing_events_yesterday()
        message = ""
        for item in res:
            message += "{}: from '{}' to '{}' amount {} for fee {:.2f}\n".format(
                item["date"],
                item["alias_in"],
                item["alias_out"],
                self.__sats_format(item["amount"]),
                item["fee_msats"] / 1000,
            )
        return message

    def initial_info(self) -> str:
        message = "{}".format(self.__date_str())
        message += "{}".format(self.__channel_alias())
        message += "{}".format(self.__active_channels())
        message += "{}".format(self.__inactive_channels())
        message += "{}\n".format(self.__line())
        return message

    def summary_all_time(self) -> str:
        message = "\nSummary all time:\n"
        message += "{}\n".format(self.__line())
        message += "{}".format(self.__count_routing_tx_all())
        message += "{}".format(self.__routing_all())
        message += "{}".format(self.__fee_all())
        message += "{}\n".format(self.__line())
        return message

    def summary_yesterday(self) -> str:
        message = "Summary yersterday:"
        message += "\n{}\n".format(self.__line())
        message += "{}".format(self.__count_routing_tx_yesterday())
        message += "{}".format(self.__routing_yesterday())
        message += "{}\n".format(self.__fee_yesterday())
        return message

    def __str__(self) -> str:
        message = self.initial_info()
        message += self.balance()
        message += self.summary_all_time()
        message += self.summary_yesterday()
        return message

    def __line(self) -> str:
        return 36 * "-"

    def __btc_format(elf, value: float) -> str:
        return "{:.8f}".format(value)

    def __sats_format(self, value: int) -> str:
        return "{:,d}".format(value).replace(",", " ")

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
