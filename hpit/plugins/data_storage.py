from hpitclient import Plugin

from pymongo import MongoClient

from hpit.management.settings_manager import SettingsManager
settings = SettingsManager.get_plugin_settings()

class DataStoragePlugin(Plugin):

    def __init__(self, entity_id, api_key, logger, args=None):
        super().__init__(entity_id, api_key)
        self.logger = logger
        self.mongo = MongoClient(settings.MONGODB_URI)
        self.db = self.mongo[settings.MONGO_DBNAME].data_storage

    def post_connect(self):
        super().post_connect()

        self.subscribe({
            "tutorgen.store_data":self.store_data_callback,
            "tutorgen.retrieve_data":self.retrieve_data_callback,
            "tutorgen.remove_data":self.remove_data_callback})

    def store_data_callback(self, message):
        if self.logger:
            self.send_log_entry("STORE_DATA")
            self.send_log_entry(message)
        try:
            key = message["key"]
            data = message["data"]
        except KeyError:
            self.send_response(message["message_id"],{"error":"Error: store_data message must contain a 'key' and 'data'","success":False})
            return
            
        insert = self.db.update({"key":key,"entity_id":message["sender_entity_id"]},{"$set":{"data":data,}},upsert=True)
        self.send_response(message["message_id"],{"success":True})

    def retrieve_data_callback(self, message):
        if self.logger:
            self.send_log_entry("RETRIEVE_DATA")
            self.send_log_entry(message)
        
        try:
            key = message["key"]
        except KeyError:
            self.send_response(message["message_id"],{"error":"Error: retrieve_data message must contain a 'key'","success":False})
            return
            
        data = self.db.find_one({"key":key,"entity_id":message["sender_entity_id"]})
        if data == None:
            self.send_response(message["message_id"],{"error":"Key "+ str(key)+ " does not exist.","success":False})
        else:
            self.send_response(message["message_id"],{"data":data["data"],"success":True})
            
    def remove_data_callback(self, message):
        if self.logger:
            self.send_log_entry("REMOVE_DATA")
            self.send_log_entry(message)
        
        try:
            key  = message["key"]
        except KeyError:
            self.send_response(message["message_id"],{"error":"Error: remove_data message must contain a 'key'","success":False})
            return
            
        response = self.db.remove({"key":key,"entity_id":message["sender_entity_id"]})
        if response["n"] == 0:
            self.send_response(message["message_id"],{"error":"Key "+ str(key)+ " does not exist.", "success":False})
        else:
            self.send_response(message["message_id"],{"success":True})
