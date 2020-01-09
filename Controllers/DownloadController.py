from flask import Blueprint, jsonify, send_file, request, make_response
from flask import current_app as app
import app
import json
from bson.objectid import ObjectId
from bson.json_util import dumps
from gridfs import GridFS
from flask_pymongo import PyMongo
from pymongo import MongoClient
#from Controllers.DownloadController import DownloadController
#from Services.AuthenticationService import Authentication
from Models.DataObject import DataObject
from Models.Dataset import Dataset


#Authentication = Authentication()

#MongoDB Configuration
db = app.db.test
print("test db configured")

#Module that makes it easier to read files from the database using chunks
grid_fs = GridFS(db)

download = Blueprint("DownloadEndpoints",__name__, url_prefix="/download")

@download.route("/", methods=["GET"])
def index():
    datasetCollection = db.dataset
    return "number of items in dataset collection: "+str(datasetCollection.find().count())


#Displays all of the available files
@download.route("/data", methods=["GET"])
def getAll():
    #set a variable for the database 
    data = mongo.db.fs.files

    #Empty array that collects all of the file information to display
    result = []

    #Loop to gather all of the file information to display 
    for field in data.find():
        result.append({'_id': str(field['_id']), 'filename': field['filename'], 'contentType': field['contentType'], 'md5':field['md5'], 'chunkSize': field['chunkSize'], 'time': field['uploadDate']})
    return jsonify(result)

@download.route('/file/<request>', methods=['GET','POST'])
def file(request):
    #Finds the file in the database from the requested file (comes from the front end)
    grid_fs_file = grid_fs.find_one({'filename': request})
    #Function from flask that makes it easy to create a response to send to the user requesting the download
    response = make_response(grid_fs_file.read())
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers["Content-Disposition"] = "attachment; filename={}".format(request)
    return response

@download.route("/<dataset_id>")
def getDataset(dataset_id):
    #Get the dataset as json object
    data = db.dataset.find_one({"_id":ObjectId(dataset_id)})
    if data==None:
        return "Dataset with specified id not found."
    json_1 = dumps(data)
    
    #Get all data_objects that belong to dataset
    data_object = db.data_object.find({"dataSetId":ObjectId(dataset_id)})
    #Put all data_objects into one json object
    json_2 = dumps(data_object)
    
    #Combine the 2 json objects
    #ret = {"dataset":json_1, "data_objects":json_2}
    ret = json_1

    return ret