from db import DB
from os.path import exists
from datetime import datetime


class Logger:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    def __init__(self, file_url: str, db: DB, loggin_level="INFO") -> None:
        self.file_url = file_url
        self.loggin_level = loggin_level
        self.db = db
        self.__check_or_create_file()

    def __check_or_create_file(self) -> None:
        if not exists(self.file_url):
            fp = open(self.file_url, "x")
            fp.close()

    def __write_log_to_db(self, level: str, message: str) -> None:
        if not self.db.write_log(level, message):
            self.__write_log_to_file("ERROR", "Could not write log to PostgresSQL")

    def __check_logging_level(self, level_fired: str) -> bool:
        if self.loggin_level == level_fired:
            return True
        if (
            level_fired == "WARNING" or level_fired == "ERROR"
        ) and self.loggin_level == "INFO":
            return True
        if level_fired == "ERROR" and self.loggin_level == "WARNING":
            return True
        return False

    def __write_log_to_file(self, level: str, message: str) -> None:
        with open(self.file_url, "a") as file:
            file.write(self.__create_log_line(level, message) + "\n")

    def __create_log_line(self, level: str, message: str) -> str:

        now = datetime.now()
        return "{}:{}:{}".format(now.strftime("%Y-%m-%d %H:%M:%S"), level, message)

    def __log_new_message(self, level: str, message: str) -> None:
        if self.__check_logging_level(level):
            self.__write_log_to_db(level, message)
            self.__write_log_to_file(level, message)
        else:
            print("log level not met")

    def info(self, message: str) -> None:
        self.__log_new_message(self.INFO, message)

    def debug(self, message: str) -> None:
        self.__log_new_message(self.DEBUG, message)

    def warning(self, message: str) -> None:
        self.__log_new_message(self.WARNING, message)

    def error(self, message: str) -> None:
        self.__log_new_message(self.ERROR, message)
