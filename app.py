from flask import Flask
from flask import render_template
import pymongo
import json
from bson import json_util
from bson.json_util import dumps
from datetime import datetime
import time

app = Flask(__name__)
connection = pymongo.MongoClient(port=27017)

@app.route("/")
def index():
    return render_template("index.html")


def connect_to_mongo_return_metrics_with_tag(tag, connection):
    client = connection
    db_metrics = client.robotDB.metrics
    documents = db_metrics.find({'tagCounts.' + tag: {"$exists": True}})
    json_doc = json_to_doc(documents)
    
    return json_doc

def connect_to_mongo_return_metrics(connection):
    client = connection
    db_metrics = client.robotDB.metrics
    documents = db_metrics.find({})
    json_doc = json_to_doc(documents)
    
    return json_doc

def connect_to_mongo_return_testcase(connection):
    client = connection
    db_testcase = client.robotDB.testcases
    documents = db_testcase.find({})
    json_doc = json_to_doc(documents)
    
    return json_doc

def connect_to_mongo_return_metrics_with_router(connection):
    lst = []
    client = connection
    db_testcase = client.robotDB.metrics
    document1 = db_testcase.find({"routerModel" : {"$ne" : None}})

    for t in document1:
        date_time_str = t['timeStamp']
        router_model = t['routerModel']
        date_time_obj =date_time_str.split(' ')[0]
        date_stamp = datetime(int(date_time_obj[0:4]), int(date_time_obj[4:6]), int(date_time_obj[6:8]))
        result = date_stamp.strftime('%m/%d/%y')
        #   lst is in the form of list in a list: ex. ["05/08/20", "SAC2V1K"]
        lst.append((result, router_model))
    
    json_doc = json_to_doc(lst)
    return json_doc


def json_to_doc(documents):
    json_doc = []
    for doc in documents:
        json_doc.append(doc)
    json_doc = json.dumps(json_doc, default=json_util.default)
    return json_doc

@app.route("/sanity")
def sanity_chart():   
    json_doc = connect_to_mongo_return_metrics_with_tag("Sanity", connection)
    return json_doc

@app.route("/fw_regression")
def fw_chart():
    json_doc = connect_to_mongo_return_metrics_with_tag("FW_Regression", connection)
    return json_doc

@app.route("/osc_regression")
def osc_chart():
    json_doc = connect_to_mongo_return_metrics_with_tag("OSC-Regression", connection)
    return json_doc

@app.route("/scl_regression")
def scl_chart():
    json_doc = connect_to_mongo_return_metrics_with_tag("SCL-Regression", connection)
    return json_doc

@app.route("/metrics")
def router_compare():
    json_doc = connect_to_mongo_return_metrics(connection)
    return json_doc

@app.route("/testcases")
def testcase():
    json_doc = connect_to_mongo_return_testcase(connection)
    return json_doc

@app.route("/router_usage")
def router_usage():
    json_doc = connect_to_mongo_return_metrics_with_router(connection)
    return json_doc

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True)