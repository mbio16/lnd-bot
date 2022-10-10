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
        return "Date: \t{} \n".format(date.today().strftime("%Y-%m-%d"))

    def __active_channels(self) -> str:
        return "Active channels: \t{} \n".format(self.api.get_num_active_channels())

    def __inactive_channels(self) -> str:
        return "Inactive channels: \t{} \n".format(
            str(self.api.get_num_passive_channels())
        )

    def routing_all(self) -> str:
        value = self.__btc_format(self.db.get_sum_routing_all())
        return "Routing all [BTC]: \t{} \n".format(value)

    def fee_all(self) -> str:
        value = self.__sats_format(self.db.get_fee_routing_all_sats())
        return "Fee all [sats]: \t{} \n".format(value)

    def routing_yesterday(self) -> str:
        value = self.__btc_format(self.db.get_sum_routing_yesterday())
        return "Routing yesterday [BTC]: \t{} \n".format(value)

    def fee_yesterday(self) -> str:
        value = self.__sats_format(self.db.get_fee_yesterday_sats())
        return "Fee yesterday [sats]: \t{} \n".format(value)

    def count_routing_tx_all(self) -> str:
        value = self.__sats_format(self.db.get_tx_routing_count_all())
        return "TXs: \t{}".format(value)

    def count_routing_tx_yesterday(self) -> str:
        value = self.__sats_format(self.db.get_tx_routing_count_yesterday())
        return "TX: \t{}".format(value)

    def balance(self)->str:
        res = self.db.get_balance()
        message = ""
        message += "Date: \t\t{} \n".format(res["date"])
        message += "Inbound: \t{} \n".format(self.__sats_format(res["inbound"]))
        message += "Outbound: \t{} \n".format(self.__sats_format(res["outbound"]))
        message += "Onchain: \t{} \n".format(self.__sats_format(res["onchain"]))
        message += "Pending: \t{} \n".format(self.__sats_format(res["pending"]))
        return message 
    def __btc_format(self, value: float) -> str:
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
