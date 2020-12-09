from Models.AgriWatchView import AgriWatchView
from Models.Dataset import Dataset
from Services.AuthenticationService import AuthenticationService
from Services.DatasetService import DatasetService
from mongoengine import ValidationError

AuthenticationService = AuthenticationService()

class AgriWatchViewService():
    def __init__(self):
        return

    def createView(self, request):
        try:
            # Get the user to establish view ownership
            user = AuthenticationService.verifySessionAndReturnUser(request.cookies["SID"])
            if (not user):
                return {"message": "Invalid session", "status": 400}

            # Get the dataset to link view to dataset
            datasetId = request.get("dataset")
            dataset = Dataset.objects.get(id=datasetId)
            if (not dataset):
                return {"message": "Invalid dataset ID", "status": 400}

            viewAuthor = user
            viewDataset = dataset
            viewVisualtype = request.get("visualType")
            viewXData = request.get("xData")
            viewYData = request.get("yData")
            viewName = dataset + "/" + viewVisualtype

            # Create and save view object
            view = AgriWatchView(
                name = viewName,
                author = viewAuthor,
                dataset = viewDataset,
                visualtype = viewVisualtype,
                xData = viewXData,
                yData = viewYData
            )
            view.save()

            return view

        except ValidationError as e:
            print(e)
            return None

    # create object with all view info
    def makeViewObject(self, view):
        viewDataset = Dataset.objects.get(id=view.dataset.id)
        viewObject = {
            "name": view.name,
            "dataset": viewDataset,
            "visualType": view.visualType,
            "xData": view.xData,
            "yData": view.yData 
        }
        return viewObject