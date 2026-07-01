from fastapi import FastAPI
from src.plot_dashboard import *
from src.report_production import *
from src.alarm import *
from dotenv import load_dotenv
import os
import boto3
import pandas as pd
from pydantic import BaseModel
from typing import Optional, List
from src.querytag import *
from src.forecast import *
from fastapi import FastAPI, UploadFile, File, Form
# from src.documentsprocessing import pdf2s3vector_function, querytag_function

load_dotenv()
app = FastAPI()

# Config
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE')
REGION_DYNAMODB_TABLE = os.getenv('REGION_DYNAMODB_TABLE')

S3_BUCKET = os.getenv('S3_BUCKET')
REGION_S3_BUCKET = os.getenv('REGION_S3_BUCKET')

dynamodb = boto3.resource('dynamodb', region_name=REGION_DYNAMODB_TABLE)
s3 = boto3.client('s3', region_name=REGION_S3_BUCKET)

S3_VECTOR_BUCKET = os.getenv('S3_VECTOR_BUCKET')
REGION_S3_VECTOR_BUCKET = os.getenv('REGION_S3_VECTOR_BUCKET')
s3_vector = boto3.client('s3', region_name=REGION_S3_VECTOR_BUCKET)

@app.get("/")
def read_root():
    return {"message": "Hello from GENAI Machine on EC2!"}

class PlotDashboardRequest(BaseModel):
    sensor_ids: List[str]
    start_time: str
    end_time: str
    aggregation: Optional[str] = 'raw'
    factory_id: Optional[str] = 'F_xGc676J6PH'

@app.post("/plotdashboard")
def api_plotdashboard(input_data: PlotDashboardRequest):
    input_data = input_data.dict()
    prefix_s3 = 'plots'
    if not input_data:
        return {"error": "No input data provided."}
    output = plotdashboard(input_data, dynamodb, s3, prefix_s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET)
    return output

class ReportProductionRequest(BaseModel):
    datetime: str
    type: Optional[str] = ''
    type_report: Optional[str] = 'daily'
    factory_id: Optional[str] = 'F_xGc676J6PH'
    
@app.post("/reportproduction")
def api_reportproduction(input_data: ReportProductionRequest):
    input_data = input_data.dict()
    prefix_s3 = 'reports'
    if not input_data:
        return {"error": "No input data provided."}
    if input_data['type'] == 'PD1KT':    
        output = reportproduction_PD1KT(input_data, dynamodb, s3, prefix_s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET)
    return output

class AlarmRequest(BaseModel):
    datetime: str
    # type: Optional[str] = ''
    # type_report: Optional[str] = 'daily'
    factory_id: Optional[str] = 'F_xGc676J6PH'
    
@app.post("/alarm")
def api_alarm(input_data: AlarmRequest):
    input_data = input_data.dict()
    if not input_data:
        return {"error": "No input data provided."}
    output = alarm(input_data, dynamodb, s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET)
    return output

class QueryTag(BaseModel):
    inputText: Optional[str] = 'Nồng độ oxi đầu lò hiện tại là bao nhiêu?. Hiện tại: 14:00:00 ngày 07/07/2025'
    
@app.post("/querytag")
def api_querytag(input_data: QueryTag):
    input_data = input_data.dict()
    if not input_data:
        return {"error": "No input data provided."}
    output = querytag_function(input_data)
    return output

class Forecasting(BaseModel):
    sensor_ids: List[str] = ["4G1GA01XAC01_O2"]
    start_time: str = "2025-07-08T06:00:00"
    end_time: str = "2025-07-08T14:00:00"
    aggregation: Optional[str] = 'raw'
    factory_id: Optional[str] = 'F_xGc676J6PH'
    
@app.post("/forecast")
def api_forecast(input_data: Forecasting):
    input_data = input_data.dict()
    prefix_s3 = 'plots'
    if not input_data:
        return {"error": "No input data provided."}
    output = forecast_function(input_data, dynamodb, s3, prefix_s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET)
    return output

# @app.post("/pdf2s3vector", tags=["DocumentsProcessing"])
# async def api_pdf2s3vector(file: UploadFile = File(...)):
#     if not file:
#         return {"error": "No file provided."}
#     else:
#         output = pdf2s3vector_function(file, dynamodb, s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET)
#         return output

# @app.post("/queryvector", tags=["DocumentsProcessing"])
# async def api_queryvector(inputText: str = Form(...)):
#     if not inputText:
#         return {"error": "No input text provided."}
#     output = {"message": f"Querying vector database with input: {inputText}"}
#     return output