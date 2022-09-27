import psycopg2
import json
from datetime import datetime

# from logger import Logger


class DB:
    def __init__(
        self, db: str, user: str, password: str, host: str, port: int = 5432
    ) -> None:
        # connecting to db
        self.conn = psycopg2.connect(
            database=db, user=user, password=password, host=host, port=port
        )
        self.cursor = self.conn.cursor()  # creating a cursor

    def write_tx_to_db(self, content_list: list, logger) -> None:
        logger.info("Start writting channels to DB.")
        for item in content_list:
            self.__check_channel_in_db(
                item["chan_id_in"], item["public_key_in"], item["chan_in_alias"], logger
            )
            self.__check_channel_in_db(
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

    def __check_channel_in_db(
        self, channel_id: int, public_key: str, alias: str, logger
    ) -> None:
        # print(channel_id)
        self.cursor.execute(
            "SELECT sum(channel_id) FROM channels WHERE channel_id = %s;", (channel_id,)
        )
        res = self.cursor.fetchone()
        if res[0] is None:
            logger.info("Channel not in DB, writting it.")
            self.cursor.execute(
                "INSERT INTO channels (channel_id,remote_public_key,alias) VALUES (%s,%s,%s);",
                (channel_id, public_key, alias),
            )
            self.debug(
                "Channel to be written: {},{},{}".format(
                    str(channel_id), str(public_key), str(alias)
                )
            )
            self.conn.commit()
        logger.info("Channel written to DB.")

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

    def write_log(self, level: str, message: str) -> bool:
        try:
            query = """INSERT INTO public.logs 
                            (log_type, log_timestamp, message) 
                        VALUES
                            ((SELECT id FROM log_type WHERE type=%s), now(),%s);"""
            values = (level, message)
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            print(str(e))
            return False

    def delete_all_invoices(self,logger)->None:
        query= """
                DELETE FROM invoices;
                ALTER SEQUENCE invoices_id_seq RESTART WITH 1;
        """
        logger.info("Deleting from invoices...")
        logger.info("Restarting sequence to 1...")
        self.cursor.execute(query)
        self.conn.commit()
        
        
    def get_youngest_unixtimestamp_routing_tx(self) -> int:
        query = """
                SELECT unix_timestamp FROM routing
                ORDER BY unix_timestamp DESC
                LIMIT 1;
        """
        self.cursor.execute(query, None)
        res = self.cursor.fetchone()[0]
        if res is None:
            return int(0)
        else:
            return int(res.timestamp())
