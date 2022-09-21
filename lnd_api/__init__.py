import base64, codecs, json, requests
from datetime import date, datetime
from datetime import timedelta
import time


class LND_api:
    def __init__(
        self, base_url: str, macaroon: str, cert_path: str, validate_cert: bool
    )->None:
        self.base_url = base_url
        self.macaroon = macaroon
        self.cert_path = cert_path
        self.validate_cert = validate_cert
        self.headers = headers = {"Grpc-Metadata-macaroon": self.macaroon}

        if validate_cert == False:
            self.cert_path = False
        self.__get_basic_info()

    def __get_basic_info(self)-> None:
        urlInfo = self.base_url + "/v1/getinfo"
        r = requests.get(urlInfo, headers=self.headers, verify=self.cert_path)
        content = r.json()
        self.alias = content["alias"]
        self.color = content["color"]
        self.pub_key = content["identity_pubkey"]
        self.height = content["block_height"]
        self.num_active_channels = None
        self.num_inactive_channels = None
        self.__get_channels_status_count()

    def __str__(self) -> str:
        return self.alias

    def routing_all(self) -> tuple:
        content = self.routing_all_get_all_as_dict()
        return content, self.__get_sum_from_response(content)

    def routing_all_get_all_as_dict(self) -> dict:
        data = {
            "start_time": "0",
            "num_max_events": 50000,
        }
        content = self.__switch(data)
        content = self.__generate_aliases_for_channels(content["forwarding_events"])
        return content

    def routing_yesterday_get_all_as_dict(self) -> dict:
        yesterday_start = date.today() - timedelta(days=1)
        yesterday_start = time.mktime(yesterday_start.timetuple())
        yesterday_stop = yesterday_start + (60 * 60 * 24)
        data = {
            "start_time": str(int(yesterday_start)),
            "end_time": str(int(yesterday_stop)),
            "num_max_events": 50000,
        }
        response = self.__switch(data)
        content = self.__generate_aliases_for_channels(response["forwarding_events"])
        return content

    def routing_yesterday(self) -> tuple:

        # print(json.dumps(),indent=3)
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

    @staticmethod
    def convert_sum_to_text(sum_dict: dict) -> str:
        sum_btc = "{:.8f}".format(sum_dict["sum_btc"])
        suma_fee = "{:.2f}".format(sum_dict["sum_fee"])
        txs = sum_dict["txs"]
        return "TXs\t\t\t: {0}\nrouted [BTC]\t: {1}\nFee [sats]\t\t: {2}".format(
            txs, sum_btc, suma_fee
        )