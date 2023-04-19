import MySQLdb
import ConfigParser


class DBConnection:

    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read("config.cfg")
        user = config.get("Data", "user")
        password = config.get("Data", "password")
        schema = config.get("Data", "schema")
        self.db = MySQLdb.connect("localhost", user, password, schema)
        self.db.set_character_set('utf8')
        self.cursor = self.db.cursor()