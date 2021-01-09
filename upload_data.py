import pandas as pd 
import boto3 
import json 
from bs4 import BeautifulSoup
import pandas as pd 
from collections import Counter
import json 
from datetime import datetime 
import redis 
# import numpy
import pymongo
from pymongo import MongoClient
import sys
import uuid
from threading import Thread

documentdb_password = sys.argv[3]

aws_secret_access_key=sys.argv[2]
aws_access_key_id = sys.argv[1]
bucket_name="scp-se-automation-integration"

client = pymongo.MongoClient(f"mongodb://robot:{documentdb_password}@robot.cluster-c1yanoxlng6d.us-east-1.docdb.amazonaws.com:27017/?ssl=true&ssl_ca_certs=rds-combined-ca-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false") 

##Specify the database to be used
#ex: db = client["test"]
db = client.robotDB

# dropping for once , needs to be deleted later 
db.metrics.remove({})
db.testcases.remove({})


##Specify the collection to be used
#ex: col = db["test"]
collection1 = db.metrics
collection2 = db.testcases

# add description to function name 
def return_s3_object_bytes(aws_access_key_id,aws_secret_access_key,bucket_name, run_number, test_number, file_name ="output.xml"):
    try:
        # define the filename format 
        complete_file_name="run{0}/test{1}/{2}".format(run_number,test_number,file_name)
        print("Bucket name is", bucket_name , "and Complete file name is",complete_file_name)
        
        s3 = boto3.resource("s3",aws_access_key_id=aws_access_key_id , aws_secret_access_key=aws_secret_access_key)
        obj = s3.Object(bucket_name, complete_file_name).get()["Body"].read()
        
        return (True,obj)
    except Exception as ex:
        print("Error has occured getting the XML file out of the S3 bucket", ex)
        return (False,ex)

# add description to function name 
def parse_and_return_dataframe(byte_content, run_number):
    try:
        # initialize all vars that will be fed into dataframe
        idx = []
        name = []
        tagsActual = []
        endTime = []
        startTime = []
        status = []
        timeInSec=[]
        errorMessage = []
        #runNumber = []

        print("Starting to soupify byte content")
        soup = BeautifulSoup(byte_content, "xml")
        suites = soup.find_all("suite")

        print("Byte content has been soupified and total number of suites are",str(len(suites)))

        # generate list of all possible suites 
        for suite in suites:

            # chunks = BeautifulSoup(str(suite), "xml")
            # find all tests in a particular suite 
            tests = soup.find_all("test")
            print("Number of tests in the suite are", str(len(tests)))

            for j in range(0,len(tests)):
                endTimeDatetime = datetime.strptime(tests[j].find_all("status")[-1].attrs["endtime"], "%Y%m%d %H:%M:%S.%f")
                startTimeDatetime = datetime.strptime(tests[j].find_all("status")[-1].attrs["starttime"], "%Y%m%d %H:%M:%S.%f")
                idx.append(tests[j].attrs["id"])
                name.append(tests[j].attrs["name"])
                endTime.append(endTimeDatetime)        
                startTime.append(startTimeDatetime)
                status.append(tests[j].find_all("status")[-1].attrs["status"])
                errorMessage.append( (tests[j].find("msg",level="FAIL").text) if (tests[j].find("status").attrs["status"]=="FAIL")  else "")
                timeInSec.append((endTimeDatetime -  startTimeDatetime).total_seconds())
                tagsActual.append([item.text for item in tests[j].tags()])         
            
        print("Parsing complete , proceeding to generate dataframe")
        df = pd.DataFrame(
            {"idx":idx,
             "name":name,
             "tagsActual": tagsActual,
             "status":status,
             "errorMessage":errorMessage,
             "endTime":endTime ,
             "startTime":startTime ,
             "timeInSec":timeInSec ,
             "runNumber": run_number
            })

        df["tagsActual"] = [json.dumps(item) for item in df["tagsActual"]]    
        df = df.drop_duplicates()
        df["tagsActual"] = [json.loads(item) for item in df["tagsActual"]]
        
        return(True, df)
    except Exception as ex:
        print("Error as occured parsing the xml", ex)
        return(False,ex)

# add description to function name 
def metrics_for_run(df, byte_content, runNumber, testNumber):
    try:
        output = {}
        if 'PASS' in list(df["status"].value_counts().keys()):
            p = (df["status"].value_counts()['PASS'])
        else:
            p = 0 
        
        if 'FAIL' in list(df["status"].value_counts().keys()):
            f = (df["status"].value_counts()['FAIL'])
        else:
            f = 0 

        Id = None

        soup = BeautifulSoup(byte_content, "xml")
        
        suite = soup.find("suite")
        robottag = soup.find("robot")
        
        versionMatrixId = None
        routerModel = None
        routerFirmware = None
    
        items = suite.find_all("item")

        for item in items:
            if item.attrs["name"] == "Test Router Model":
               routerModel = item.text
            if item.attrs["name"] == "Test Firmware":
               routerFirmware = item.text
            if routerFirmware and routerModel:
                versionMatrixId = routerModel+"_v"+routerFirmware.split("-")[0]

        timeStamp = robottag.attrs["generated"]
        
        pkey = uuid.uuid1()
        output["id"] = str(pkey)
        output["passPercentage"] = str(round(((p/(p+f)) * 100 ), 2))
        output["failPercentage"] = str(round(((f/(p+f)) * 100 ), 2))
        output["numberOfTest_cases"] = str(len(df))
        output["passFailStatuses"] = { "PASS": int(p), "FAIL": int(f) } 
        output["tagCounts"] = dict(Counter([item for listitem in df["tagsActual"] for item in listitem]))
        output["versionMatrixId"] = versionMatrixId
        output["timeStamp"] = timeStamp
        output["routerModel"] = routerModel
        output["routerFirmware"] = str(routerFirmware).strip()
        output['runNumber'] = runNumber
        output['testNumber'] = testNumber
        
        return(True,output)

    except Exception as ex:
        print("Error has occured parsing metrics", ex)
        return(False,ex)

##main function
# creds to be fed into harness 
# this keeps changing 
run_number = 300 
test_number = 1 

def main(run_number, test_number):
    obj = return_s3_object_bytes(aws_access_key_id,aws_secret_access_key,bucket_name, run_number, test_number)
    if(obj[0]):
        df = parse_and_return_dataframe(obj[1], run_number)
    else:
        return None

    if(obj[0] and df[0]):
        df[1]["idx"] = ["_".join([str(sorted(list(df[1]["endTime"]), reverse=True)[0].timestamp()),item]) for item in df[1]["idx"]]

        metrics = metrics_for_run(df[1], obj[1], run_number, test_number)
    
        records = json.loads(df[1].to_json(orient ="records"))
        print("******** Inserting mertic *************")
        print(json.dumps(metrics[1], sort_keys=True, indent=4))
        #add document to Mongo
        try:
            collection1.insert_one(metrics[1])
        
        except:
            raise TypeError
        
        try:
            print("************** Inserting test *************")
            records = json.loads(df[1].to_json(orient ="records"))
            print(json.dumps(records, sort_keys=True, indent=4))
            collection2.insert_many(records)
        
        except:
            raise TypeError
        
        if(obj[0] and df[0] and metrics[0]):
            print("done")
        client.close()

# for run_number in range(0,450):
#     t = Thread(target=stuff, args=(run_number,1))
#     t.start()

for run_number in range(3,800):
    main(run_number, 1)

