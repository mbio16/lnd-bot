from db import DB
from logger import Logger
from lnd_api import LND_api
from datetime import date

class Message_creator():

    def __init__(self,db:DB,lnd_api: LND_api ,  logger: Logger) -> None:
        self.db = db
        self.logger = logger
        self.lnd_api = lnd_api
    
    def __date_str(self)->str:
        return "Date: {} \n".format(date.today().strftime("%Y-%m-%d"))
    def __active_channels(self)->str:
        return "Active channels: {} \n".format(self.api.get_num_active_channels())
    def __inactive_channels(self)->str:
        return "Inactive channels: {} \n".format(str(self.api.get_num_passive_channels()))
    
    def routing_all(self)->str:
       value = self.__btc_format(self.db.get_sum_routing_all())
       return "Routing all: {} \n".format(value) 
    
    def fee_all(self)->str:
        value = self.__sats_format(self.db.get_fee_routing_all_sats())
        return "Fee sats all: {} \n".format(value)
    
    def routing_yesterday(self)->str:
        value = self.__btc_format(self.db.get_sum_routing_yesterday())
        return "Routing yesterday: {} \n".format(value)
    
    def fee_yesterday(self)->str:
        value = self.__sats_format(self.db.get_fee_yesterday_sats())
        return "Fee sats yesterday: {} \n".format(value)
     
    def __btc_format(self,value:float)->str:
        return "{:.8f}".format(value)
    def __sats_format(self,value:int)->str:
        return "{:,d}".format(value).replace(',', ' ')
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