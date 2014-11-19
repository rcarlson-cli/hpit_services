import sure
import responses
import unittest
from mock import *

from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId

from couchbase import Couchbase
import couchbase

import requests

from hpit.plugins import SkillManagementPlugin

from hpit.management.settings_manager import SettingsManager
settings = SettingsManager.get_plugin_settings()

class TestSkillManagementPlugin(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        options = {
                "authType":"sasl",
                "saslPassword":"",
                "bucketType":"memcached",
                "flushEnabled":1,
                "name":"test_skill_cache",
                "ramQuotaMB":100,
            }
        req = requests.post(settings.COUCHBASE_BUCKET_URI,auth=settings.COUCHBASE_AUTH, data = options)
              
    @classmethod
    def tearDownClass(cls):
        r = requests.delete(settings.COUCHBASE_BUCKET_URI + "/test_skill_cache",auth=settings.COUCHBASE_AUTH)
        if r.status_code != 200 and r.status_code != 404:
            if r.json()['_'] != "Bucket deletion not yet complete, but will continue.\r\n":
                raise Exception(' '.join(["Failure to delete bucket:", str(r.status_code), r.text]))
    
    def setUp(self):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """      
        
        self.test_subject = SkillManagementPlugin(123,456,None)
        self.test_subject.cache = Couchbase.connect(bucket = "test_skill_cache", host = settings.COUCHBASE_HOSTNAME)
       
        self.test_subject.send_response = MagicMock()
       
    def tearDown(self):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
            
        client = MongoClient()
        client.drop_database(settings.MONGO_DBNAME)
        
        self.test_subject = None


    def test_constructor(self):
        """
        SkillManagementPlugin.__init__() Test plan:
            -ensure name, logger set as parameters
            -ensure that mongo is an instance of mongo client
            -ensure that a cache db is set up
        """
        
        test_subject = SkillManagementPlugin(123,456,None)
        test_subject.logger.should.equal(None)
        
        isinstance(test_subject.mongo,MongoClient).should.equal(True)
        isinstance(test_subject.db,Collection).should.equal(True)
        
        isinstance(test_subject.cache,couchbase.connection.Connection).should.equal(True)
    
    def test_get_skill_name_callback(self):
        """
        SkillManagementPlugin.get_skill_name_callback() Test plan:
            - pass in message without id, should respond with error
            - pass in message with bogus id, should respond with error
            - pass in message with good id, should respond with name
        """        
        real_id = self.test_subject.db.insert({"skill_name":"addition"})
        msg= {"message_id":"1","skill_id":real_id}
        self.test_subject.get_skill_name_callback(msg)
        self.test_subject.send_response.assert_called_with("1",{
                "skill_name":"addition",
                "skill_id": str(real_id),
        })
            
    def test_get_skill_name_callback_no_skill_id(self):
        """
        SkillManagementPlugin.get_skill_name_callback() No Skill Id
        """
        msg = {"message_id":"1"}
        self.test_subject.get_skill_name_callback(msg)
        self.test_subject.send_response.assert_called_with("1",{
                "error":"Message must contain a 'skill_id'",
        })
        
    def test_get_skill_name_callback_invalid_id(self):
        """
        SkillManagementPlugin.get_skill_name_callback() Invalid Skill Id
        """
        msg= {"message_id":"1","skill_id":"foo"}
        self.test_subject.get_skill_name_callback(msg)
        self.test_subject.send_response.assert_called_with("1",{
                "error":"'skill_id' is not a valid ObjectId"      
        })
    
    def test_get_skill_name_callback_no_exist_skill(self):
        """
        SkillManagementPlugin.get_skill_name_callback() Skill Id Does Not Exist
        """
        bogus_id = ObjectId()
        msg= {"message_id":"1","skill_id":bogus_id}
        self.test_subject.get_skill_name_callback(msg)
        self.test_subject.send_response.assert_called_with("1",{
                "error":"Skill with id " + str(bogus_id) + " does not exist."      
        })
    
    def test_get_skill_id_callback_no_skill_name(self):
        """
        SkillManagementPlugin.get_skill_id_callback() Test plan:
            - pass in message without name, should respond with error
            - pass in message with name for non existent, should create one
            - pass in message with existing name, should return proper id
        """
                
        msg = {"message_id":"1"}
        self.test_subject.get_skill_id_callback(msg)
        self.test_subject.send_response.assert_called_with("1",{
                "error":"Message must contain a 'skill_name'",
        })
        
    def test_get_skill_id_callback_new_skill(self):
        """
        SkillManagementPlugin.get_skill_id_callback() New Skill
        """
        msg = {"message_id":"1","skill_name":"new_addition"}
        self.test_subject.get_skill_id_callback(msg)
        self.test_subject.db.find({"skill_name":"new_addition"}).count().should.equal(1)
        added_id = self.test_subject.db.find_one({"skill_name":"new_addition"})["_id"]
        self.test_subject.send_response.assert_called_with("1",{
                "skill_name":"new_addition",
                "skill_id":str(added_id),
                "skill_model":"Default",
                "cached":False
        })
        
    def test_get_skill_id_callback_existing_skill(self):
        """
        SkillManagementPlugin.get_skill_id_callback() Existing Skill
        """
        self.test_subject.cache.set("Defaultaddition","123")
        
        msg = {"message_id":"1","skill_name":"addition"}
        self.test_subject.get_skill_id_callback(msg)
        self.test_subject.send_response.assert_called_with("1",{
                "skill_name":"addition",
                "skill_id":"123",
                "skill_model":"Default",
                "cached":True
        })
        
        
        
