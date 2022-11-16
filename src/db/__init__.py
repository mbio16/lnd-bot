import psycopg2
import json
from datetime import datetime, date, timedelta
# from logger import Logger


class DB:
    SATS_TO_BTC = 100000000
    MSATS_TO_SATS = 1000

    def __init__(
        self, db: str, user: str, password: str, host: str, port: int = 5432
    ) -> None:
        # connecting to db
        self.conn = psycopg2.connect(
            database=db, user=user, password=password, host=host, port=port
        )
        self.cursor = self.conn.cursor()  # creating a cursor
        if self.__is_db_cleared():
            self.create_schema()

    def create_schema(self) -> None:
        with open("./sql-scripts/create-schemas.sql", "r") as sql_file:
            query = sql_file.read()
            self.cursor.execute(query)
            self.conn.commit()

    def __is_db_cleared(self) -> bool:
        query = """
                    SELECT count(*) FROM pg_catalog.pg_tables
                    WHERE schemaname != 'information_schema' AND
                    schemaname != 'pg_catalog';
                """
        self.cursor.execute(query)
        res = self.cursor.fetchone()
        return int(res[0]) == 0

    def write_tx_to_db(self, content_list: list, logger) -> None:
        logger.info("Start writting channels to DB.")
        for item in content_list:
            self.check_channel_in_db(
                item["chan_id_in"], item["public_key_in"], item["chan_in_alias"], logger
            )
            self.check_channel_in_db(
                item["chan_id_out"],
                item["public_key_out"],
                item["chan_out_alias"],
                logger,
            )
            logger.info("Channels written to DB.")
            logger.info("Start writing Txs to DB.")
            self.__write_routing_tx(item, logger)
            logger.info("Written TXs to DB.")
        logger.info("Done writting channels to DB.")

    def check_channel_in_db(
        self, channel_id: int, public_key: str, alias: str, logger
    ) -> None:
        if not self.is_channel_in_db(channel_id):
            logger.info("Channel not in DB, writting it.")
            self.cursor.execute(
                "INSERT INTO channels (channel_id,remote_public_key,alias) VALUES (%s,%s,%s);",
                (channel_id, public_key, alias),
            )
            logger.debug(
                "Channel to be written: {},{},{}".format(
                    str(channel_id), str(public_key), str(alias)
                )
            )
            self.conn.commit()
        logger.info("Channel written to DB.")

    def is_channel_in_db(self,channel_id:int)->bool:
         # print(channel_id)
        self.cursor.execute(
            "SELECT sum(channel_id) FROM channels WHERE channel_id = %s;", (channel_id,)
        )
        res = self.cursor.fetchone()[0]
        if res is None:
            return False
        elif res == 0:
            return False
        else:
            return True
            
        
    def __write_routing_tx(self, content: dict, logger) -> None:
        query = """
        INSERT INTO public.routing 
        (unix_timestamp, chan_id_in, chan_id_out, amount_in_sats, amount_out_sats, fee_sats, fee_milisats, amt_in_milisats, amount_out_milisats)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        values = (
            datetime.fromtimestamp(int(content["timestamp"])),
            content["chan_id_in"],
            content["chan_id_out"],
            content["amt_in"],
            content["amt_out"],
            content["fee"],
            content["fee_msat"],
            content["amt_in_msat"],
            content["amt_out_msat"],
        )
        logger.info("Writting TX...")
        logger.debug("Routing TX values: {}".format(str(values)))
        self.cursor.execute(query, values)
        self.conn.commit()

    def write_invoices(self, invoices: list, logger) -> None:
        logger.info("Start writing invoices to DB.")
        for invoice in invoices:
            query = """
                INSERT INTO public.invoices (memo, value, value_milisats, settled, creation_date, settle_date, state, expiry)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s);
            """
            values = (
                invoice["memo"],
                int(invoice["value"]),
                int(invoice["value_msat"]),
                invoice["settled"],
                datetime.fromtimestamp(int(invoice["creation_date"])),
                datetime.fromtimestamp(int(invoice["settle_date"])),
                invoice["state"],
                int(invoice["expiry"]),
            )
            self.cursor.execute(query, values)
            self.conn.commit()

    def write_log(self, level: str, message: str,host_name:str) -> bool:
        try:
            query = """INSERT INTO public.logs 
                            (log_type, log_timestamp, message,host_name) 
                        VALUES
                            ((SELECT id FROM log_type WHERE type=%s), now(),%s,%s);"""
            values = (level, message,host_name)
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            print(str(e))
            return False

    def delete_all_invoices_that_are_open(self, logger) -> None:
        if not self.__is_invoices_empty_table(logger):
            logger.info("Empty table.. returning 0")
            return 0
        query = """
                SELECT min(id) FROM invoices WHERE state = 'OPEN';
                """
        alter_offset_min = self.__get_offset_index_by_query(query)
        if alter_offset_min is None:
            logger.info("Returning max(id) from invoices.")
            query = "SELECT max(id) FROM invoices;"
            offset = self.__get_offset_index_by_query(query)
            logger.debug("Offset: {}".format(str(offset)))
            return offset
        else:
            query = """
                    DELETE FROM invoices where id>=%s;
                    ALTER SEQUENCE invoices_id_seq RESTART WITH  %s;"""
            values = (alter_offset_min, int(alter_offset_min))
            logger.info("Deleting from invoices...")
            logger.info("Restarting sequence to {}...".format(str(alter_offset_min)))
            self.cursor.execute(query, values)
            self.conn.commit()
            return alter_offset_min

    def __get_offset_index_by_query(self, query: str) -> int:
        self.cursor.execute(query, None)
        self.conn.commit()
        offset = self.cursor.fetchone()[0]
        return offset

    def __is_invoices_empty_table(self, logger) -> bool:
        query = """
                SELECT count(*) FROM invoices;
                """
        self.cursor.execute(query, None)
        self.conn.commit()
        num_records = self.cursor.fetchone()[0]
        logger.debug("Is invoices empty: {}".format(str(num_records)))
        return num_records > 0

    def get_youngest_unixtimestamp_routing_tx(self) -> int:
        query = """
                SELECT unix_timestamp FROM routing
                ORDER BY unix_timestamp DESC
                LIMIT 1;
        """
        self.cursor.execute(query, None)
        try:
            res = self.cursor.fetchone()[0]
        except:
            return 0
        if res is None:
            return int(0)
        else:
            return int(res.timestamp())

    def write_payments_to_db(self, payment_list: list) -> None:
        for payment in payment_list:
            query = """
            INSERT INTO payments 
            (value, value_milisat, creation_date, fee, fee_milisat, status, index_offset) 
            VALUES(%s, %s, %s, %s, %s, %s, %s);
            """
            values = (
                int(payment["value_sat"]),
                int(payment["value_msat"]),
                datetime.fromtimestamp(int(payment["creation_date"])),
                int(payment["fee_sat"]),
                int(payment["value_msat"]),
                payment["status"],
                int(payment["payment_index"]),
            )
            self.cursor.execute(query, values)
        self.conn.commit()

    def write_channel_backup(self, data: dict, logger) -> None:
        logger.info("Writting channel backup to DB...")
        query = """
                INSERT INTO public.channel_backup (date_creation, "data") 
                VALUES(NOW(), %s);"""
        values = (json.dumps(data),)
        self.cursor.execute(query, values)
        self.conn.commit()

    def get_last_index_offset(self) -> int:
        query = """
                SELECT max(index_offset) from payments;
                """
        try:
            index = int(self.__request_query_fetch_one(query, None))
            return index
        except:
            return 0

    def get_sum_routing_yesterday(self) -> float:
        yesterday_date, today_date = self.__yesterday_today_tuple()
        query = """
                SELECT sum(amount_out_sats) FROM routing WHERE
                    unix_timestamp >= %s 
                and 
                    unix_timestamp < %s;
                """
        values = (yesterday_date, today_date)

        return self.__parse_res_value_float(
            self.__request_query_fetch_one(query, values, disable_none_return=True)
            / self.SATS_TO_BTC
        )

    def get_fee_yesterday_sats(self) -> int:
        yesterday_date, today_date = self.__yesterday_today_tuple()
        query = """
                SELECT sum(fee_milisats) FROM routing WHERE
                    unix_timestamp >= %s 
                and 
                    unix_timestamp < %s;
                """
        values = (yesterday_date, today_date)
        return self.__parse_res_value(
            self.__request_query_fetch_one(query, values, disable_none_return=True)
            / self.MSATS_TO_SATS
        )

    def get_sum_routing_all(self) -> float:
        query = """
                SELECT sum(amount_out_sats) FROM routing;
                """
        return float(
            self.__parse_res_value_float(
                (self.__request_query_fetch_one(query, None, disable_none_return=True))
            )
            / self.SATS_TO_BTC
        )

    def get_fee_routing_all_sats(self) -> str:
        query = """
                SELECT sum(fee_milisats) FROM routing; 
                """
        return self.__parse_res_value(
            self.__request_query_fetch_one(query, None, disable_none_return=True)
            / self.MSATS_TO_SATS
        )

    def get_tx_routing_count_all(self) -> int:
        query = """
                SELECT count(id) from routing;
                """
        return self.__parse_res_value(
            self.__request_query_fetch_one(query, None, disable_none_return=True)
        )

    def get_tx_routing_count_yesterday(self) -> int:
        query = """
                SELECT count(id) FROM routing WHERE
                 unix_timestamp >= %s 
                and 
                 unix_timestamp < %s;
                """
        yesterday_date, today_date = self.__yesterday_today_tuple()
        values = (yesterday_date, today_date)
        return self.__parse_res_value(
            self.__request_query_fetch_one(query, values, disable_none_return=True)
        )

    def get_routing_events_yesterday(self) -> list:
        yesterday_date, today_date = self.__yesterday_today_tuple()
        values = (yesterday_date, today_date)
        query = """
                SELECT unix_timestamp,alias_in,alias_out, amount_out_sats, fee_milisats
                FROM routing_completed
                WHERE
                 unix_timestamp >= %s 
                and 
                 unix_timestamp < %s;
                """
        self.cursor.execute(query, values)
        res = self.cursor.fetchall()
        result = list()
        for item in res:
            result.append(
                {
                    "date": item[0].strftime("%Y-%m-%d %H:%M:%S"),
                    "alias_in": item[1],
                    "alias_out": item[2],
                    "amount": item[3],
                    "fee_msats": item[4],
                }
            )
        return result

    def write_balance(self, data: dict) -> None:
        query = """
                INSERT INTO public.balance (unix_timestamp, inbound_sats, outbound_sats, onchain, pending_open_balance)
                VALUES(NOW(), %s, %s, %s, %s);
                """
        values = (data["inbound"], data["outbound"], data["onchain"], data["pending"])
        self.cursor.execute(query, values)
        self.conn.commit()

    def get_balance(self) -> dict:
        query = """
                SELECT unix_timestamp, inbound_sats, outbound_sats, onchain, pending_open_balance 
                FROM public.balance
                ORDER BY unix_timestamp DESC
                LIMIT 1;
                """
        self.cursor.execute(query)
        res = self.cursor.fetchall()[0]
        return {
            "date": res[0].strftime("%Y-%m-%d %H:%M:%S"),
            "inbound": res[1],
            "outbound": res[2],
            "onchain": res[3],
            "pending": res[4],
        }

    def write_failed_htlc(self,failed_dict:dict)->None:
        query = """
                INSERT INTO public.failed_htlc (incoming_channel_id, outgoing_channel_id, event_type, wire_failure, failure_detail, incoming_amount_msats, outgoing_amount_msats, unix_timestamp) 
                VALUES(%s,%s, %s, %s, %s, %s, %s, %s);
                """
        values = (
            failed_dict["chan_in"],
            failed_dict["chan_out"],
            failed_dict["event_type"],
            failed_dict["wire_failure"],
            failed_dict["failure_detail"],
            failed_dict["incoming_amount_msats"],
            failed_dict["outgoing_amount_msats"],
            failed_dict["time"]
        )
        self.cursor.execute(query,values)
        self.conn.commit()
        
    def __parse_res_value(self, data: object) -> int:
        if data is None:
            return int(0)
        else:
            return int(data)

    def __parse_res_value_float(self, data: object) -> float:
        if data is None:
            return float(0)
        else:
            return float(data)

    def __yesterday_today_tuple(self) -> tuple:
        today_date = date.today().strftime("%Y-%m-%d")
        yesterday_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        print("Today: " + str(today_date))
        print("Yesterday:" + str(yesterday_date))
        return yesterday_date, today_date

    def __request_query_fetch_one(
        self, query: str, values: tuple, disable_none_return=False
    ) -> object:
        if values is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, values)
        res = self.cursor.fetchone()[0]
        if disable_none_return and res is None:
            return 0
        else:
            return res

    