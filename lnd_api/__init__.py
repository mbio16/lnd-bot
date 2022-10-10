import base64, codecs, json, requests
from turtle import color
from datetime import date, datetime
from datetime import timedelta
from logger import Logger
import time


class LND_api:
    NUM_MAX_INVOICES = 100
    NUM_MAX_EVENTS = 50000
    NUM_MAX_PAYMENTS = 100

    def __init__(
        self,
        base_url: str,
        macaroon: str,
        cert_path: str,
        validate_cert: bool,
        logger: Logger,
    ) -> None:
        self.base_url = base_url
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.validate_cert = validate_cert
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}
        self.logger = logger
        if validate_cert == False:
            self.cert_path = False
        self.__get_basic_info()

    def __get_basic_info(self) -> None:
        urlInfo = self.base_url + "/v1/getinfo"
        self.logger.info("Sending basic info.")
        try:
            r = requests.get(urlInfo, headers=self.headers, verify=self.cert_path)
            content = r.json()
        except Exception as e:
            self.logger.error("Error when sending basic info: {}".format(str(e)))
        self.alias = content["alias"]
        self.color = content["color"]
        self.pub_key = content["identity_pubkey"]
        self.height = content["block_height"]
        self.num_active_channels = None
        self.num_inactive_channels = None
        self.__get_channels_status_count()
        self.logger.info("Basic info parsed.")
        self.logger.debug(
            "Alias: {}, Color: {}, Pubkey: {}, Block_height: {}".format(
                self.alias, self.color, self.pub_key, self.height
            )
        )

    def __str__(self) -> str:
        return self.alias

    def routing_all(self) -> tuple:
        self.logger.info("Sending request routing all.")
        content = self.routing_all_get_all_as_dict()
        return content, self.__get_sum_from_response(content)

    def routing_all_get_all_as_dict(self) -> dict:
        self.logger.info("Sending message about routing since beggining.")
        return self.routing_since_time_as_dict(0)

    def routing_yesterday_get_all_as_dict(self) -> dict:
        self.logger.info("Sending message for yesterdays routing.")
        yesterday_start = date.today() - timedelta(days=1)
        yesterday_start = time.mktime(yesterday_start.timetuple())
        yesterday_stop = yesterday_start + (60 * 60 * 24)
        data = {
            "start_time": str(int(yesterday_start)),
            "end_time": str(int(yesterday_stop)),
            "num_max_events": self.NUM_MAX_EVENTS,
        }
        return self.routing_since_time_as_dict(None, params_data=data)

    def routing_since_time_as_dict(
        self, start_time_unix: int, params_data=None
    ) -> dict:
        result_list = list()
        data = None
        while True:
            if params_data is None:
                data = {
                    "start_time": str(start_time_unix + 1),
                    "num_max_events": self.NUM_MAX_EVENTS,
                }
            else:
                data = params_data
            self.logger.debug("Data in requests: {}".format(json.dumps(data, indent=1)))
            self.logger.info("Sending request to node.")
            content = self.__switch(data)
            self.logger.info("Parsing requests from node.")
            self.logger.debug(
                "Parsing request from node: {}".format(json.dumps(content, indent=1))
            )
            result_list = result_list + content["forwarding_events"]
            if len(content["forwarding_events"]) < self.NUM_MAX_INVOICES:
                break
        result_list = self.__generate_aliases_for_channels(result_list)
        self.logger.debug(
            "Parsing request from node with aliases: {}".format(
                json.dumps(result_list, indent=1)
            )
        )
        return result_list

    def routing_yesterday(self) -> tuple:
        response = self.routing_yesterday_get_all_as_dict()
        return self.__generate_aliases_for_channels(
            response
        ), self.__get_sum_from_response(response)

    def __get_sum_from_response(self, data_list: list) -> tuple:
        if len(data_list) == 0:
            return {"txs": 0, "sum_btc": 0, "sum_fee": 0}
        suma_msat = 0
        fee_msat = 0
        pole = list()
        res = list()
        for i, item in enumerate(data_list):
            cas = datetime.fromtimestamp(int(item["timestamp"]))
            suma_msat += int(item["amt_out_msat"])
            fee_msat += int(item["fee_msat"])
        suma_btc = float(suma_msat / 1000) / pow(10, 8)
        fee_sats = float(fee_msat / 1000)
        result = {"txs": i + 1, "sum_btc": suma_btc, "sum_fee": fee_sats}
        return result

    def __switch(self, data: dict) -> dict:
        urlTX = self.base_url + "/v1/switch"
        r = requests.post(
            urlTX, headers=self.headers, verify=self.cert_path, data=json.dumps(data)
        )
        return r.json()

    def __generate_aliases_for_channels(self, responses: list) -> dict:
        hash_mapa = {}
        result_list = list()
        for response in responses:
            if response["chan_id_in"] in hash_mapa.keys():
                chan_alias_in = hash_mapa[response["chan_id_in"]]
            else:
                (
                    chan_alias_in,
                    channel_capacity,
                    public_key_in,
                ) = self.__get_nodes_in_channel(response["chan_id_in"])
                hash_mapa[response["chan_id_in"]] = chan_alias_in

            if response["chan_id_out"] in hash_mapa.keys():
                chan_alias_out = hash_mapa[response["chan_id_out"]]
            else:
                (
                    chan_alias_out,
                    channel_capacity,
                    public_key_out,
                ) = self.__get_nodes_in_channel(response["chan_id_out"])
                hash_mapa[response["chan_id_out"]] = chan_alias_out
            response["chan_in_alias"] = chan_alias_in
            response["chan_out_alias"] = chan_alias_out
            response["channel_capacity"] = channel_capacity
            response["public_key_out"] = public_key_out
            response["public_key_in"] = public_key_in
            result_list.append(response)
        return result_list

    def __get_nodes_in_channel(self, chan_id: str) -> tuple:
        url = self.base_url + "/v1/graph/edge/" + chan_id
        r = requests.get(url, headers=self.headers, verify=self.cert_path)
        # print(str(json.dumps(r.json(),indent=3)))
        response = r.json()
        if r.status_code == 200:
            ## alias and other info found
            if response["node1_pub"] == self.pub_key:
                node_to_resolver_allias = response["node2_pub"]
            else:
                node_to_resolver_allias = response["node1_pub"]
            url = self.base_url + "/v1/graph/node/" + node_to_resolver_allias
            r = requests.get(url, headers=self.headers, verify=self.cert_path)
            response = r.json()
            # print(json.dumps(response,indent=2))
            return (
                response["node"]["alias"],
                response["total_capacity"],
                response["node"]["pub_key"],
            )
        else:
            ## node not found (neznal jsem ale rip nějakému uzlu)
            return None, None, None

    def __get_channels_status_count(self) -> None:
        url = self.base_url + "/v1/channels"
        response = requests.get(
            url,
            headers=self.headers,
            verify=self.cert_path,
        )
        channel_list = response.json()["channels"]

        self.num_active_channels = 0
        self.num_inactive_channels = 0
        for item in channel_list:
            if item["active"]:
                self.num_active_channels += 1
            else:
                self.num_inactive_channels += 1

    def get_num_active_channels(self) -> int:
        return self.num_active_channels

    def get_num_passive_channels(self) -> int:
        return self.num_inactive_channels

    def invoices_since_last_offset_as_list(self, start_index_offset: int) -> list:
        sum_list = list()
        current_offset = start_index_offset
        loop_to_run = True
        self.logger.info("Preparing to send request for invoices...")
        while loop_to_run:
            params = {
                "index_offset": current_offset,
                "num_max_invoices": self.NUM_MAX_INVOICES,
            }
            self.logger.info("Request for invoices offset: {}".format(current_offset))
            self.logger.debug(
                "Request for invoices: {}".format(json.dumps(params, indent=1))
            )

            content_list = self.__invoices(params)
            sum_list.extend(content_list)
            if len(content_list) == 0:
                self.logger.info("Stopping sending request for invoices...")
                loop_to_run = False
            else:
                current_offset += self.NUM_MAX_INVOICES

        self.logger.debug("Number of invoices: {}".format(str(len(sum_list))))
        return sum_list

    def __invoices(self, params: dict) -> dict:
        try:
            urlTX = self.base_url + "/v1/invoices"
            r = requests.get(
                urlTX, headers=self.headers, verify=self.cert_path, params=params
            )
            return r.json()["invoices"]
        except Exception as e:
            self.logger.error(
                "Error when recieving requests for invoices: {}".format(str(e))
            )
            return list()

    def channel_backup_as_dict(self) -> dict:
        try:
            urlCB = self.base_url + "/v1/channels/backup"
            r = requests.get(urlCB, headers=self.headers, verify=self.cert_path)
            return r.json()
        except Exception as e:
            self.logger.error("Error when recieving channel backup: {}".format(str(e)))
            return None

    def payments_all_as_dict(self) -> list:
        self.logger.info("Sending message for all payments.")
        return self.payments_from_index_offset_as_dict(1)

    def payments_from_index_offset_as_dict(self, start_index: int) -> list:
        index_offset = start_index
        result_list = list()
        while True:
            self.logger.info(
                "Sending message for payments, max {}".format(
                    str(self.NUM_MAX_PAYMENTS)
                )
            )
            data = {
                "max_payments": self.NUM_MAX_PAYMENTS,
                "count_total_payments": True,
                "index_offset": str(index_offset),
            }
            content = self.__payments(data)
            if len(content) == 0:
                return result_list
            index_offset = content[-1]["payment_index"]
            result_list = result_list + content

    def __payments(self, params: dict) -> list:
        try:
            self.logger.debug(
                "Sending requests for paymtns with params {}".format(
                    json.dumps(params, indent=1)
                )
            )
            urlTX = self.base_url + "/v1/payments"
            r = requests.get(
                urlTX, headers=self.headers, verify=self.cert_path, params=params
            )
            return r.json()["payments"]
        except Exception as e:
            self.logger.error(
                "Error when recieving requests for payments: {}".format(str(e))
            )
            return list()

    @staticmethod
    def convert_response_routing_to_text(response: list):
        result_str = ""
        import locale

        locale.setlocale(locale.LC_ALL, "")
        for item in response:
            date_of_tx = datetime.fromtimestamp(int(item["timestamp"]))
            amount_sats = "{:,d}".format(int(item["amt_out"])).replace(",", " ")
            fee_sats = "{:,d}".format(int(item["fee"])).replace(",", " ")
            chan_in = item["chan_in_alias"]
            chan_out = item["chan_out_alias"]
            result_str += "{0}: from {1} to {2} amount {3} for fee {4}\n".format(
                date_of_tx, chan_in, chan_out, amount_sats, fee_sats
            )
        return result_str

    def balance_as_dict(self) -> dict:
        result = dict()
        res1 = self.__get_onchain_balance()
        result["onchain"] = int(res1["total_balance"])
        res2 = self.__get_ln_balance()
        result["inbound"] = int(res2["local_balance"]["sat"])
        result["outbound"] = int(res2["remote_balance"]["sat"])
        result["pending"] = int(res2["pending_open_balance"])
        return result

    def __get_ln_balance(self) -> dict:
        try:
            urlTX = self.base_url + "/v1/balance/channels"
            r = requests.get(urlTX, headers=self.headers, verify=self.cert_path)
            return r.json()
        except Exception as e:
            self.logger.error(
                "Error when recieving requests for balance channel: {}".format(str(e))
            )
            return None

    def __get_onchain_balance(self) -> dict:
        try:
            urlTX = self.base_url + "/v1/balance/blockchain"
            r = requests.get(urlTX, headers=self.headers, verify=self.cert_path)
            return r.json()
        except Exception as e:
            self.logger.error(
                "Error when recieving requests for balance channel: {}".format(str(e))
            )
            return None

    @staticmethod
    def convert_sum_to_text(sum_dict: dict) -> str:
        sum_btc = "{:.8f}".format(sum_dict["sum_btc"])
        suma_fee = "{:.2f}".format(sum_dict["sum_fee"])
        txs = sum_dict["txs"]
        return "TXs\t\t\t: {0}\nrouted [BTC]\t: {1}\nFee [sats]\t\t: {2}".format(
            txs, sum_btc, suma_fee
        )
