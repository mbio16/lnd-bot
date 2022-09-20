import psycopg2
import json
from datetime import datetime
class DB():
    
    def __init__(self,db:str,user:str,password:str,host:str,port:int=5432) -> None:
        #connecting to db
        self.conn = psycopg2.connect(database=db,
                                user=user,
                                password=password,
                                host=host,
                                port=port)
        self.cursor = self.conn.cursor()  # creating a cursor
        
    def write_tx_to_db(self,content_list:list)->None:
        for item in content_list:
            #print(str(item) + "\n")
            self.__check_channel_in_db(item["chan_id_in"],item["public_key_in"],item["chan_in_alias"])
            self.__check_channel_in_db(item["chan_id_out"],item["public_key_out"],item["chan_out_alias"])
            self.__write_routing_tx(item)
            
            
    def __check_channel_in_db(self,channel_id:int,public_key:str,alias:str)->None:
        #print(channel_id)
        self.cursor.execute("SELECT sum(channel_id) FROM channels WHERE channel_id = %s;",(channel_id,))
        res = self.cursor.fetchone()
        if res[0] is None:
            self.cursor.execute("INSERT INTO channels (channel_id,remote_public_key,alias) VALUES (%s,%s,%s);",
                                (channel_id,public_key,alias))
            self.conn.commit()
        print(res)
    def __write_routing_tx(self,content:dict)->None:
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
            content["amt_out_msat"]
        )
        self.cursor.execute(query,values)
        self.conn.commit()