# import logging
# from typing import Dict, Any
# from http import HTTPStatus
# import boto3
# from boto3.dynamodb.conditions import Key
# from datetime import datetime, timedelta
# import json
# from decimal import Decimal
# import os
# import re

# URL_WEBSOCKET = os.environ['URL_WEBSOCKET']
# DOMAIN_NAME = os.environ['DOMAIN_NAME']
# STAGE = os.environ['STAGE']
# REGION_NAME = os.environ['REGION_NAME']

# bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
# websocket_client = boto3.client(
#     "apigatewaymanagementapi",
#     endpoint_url=f"https://{DOMAIN_NAME}/{STAGE}",
#     region_name=REGION_NAME
# )
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)

# # config query dynamoDB
# dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
# table = dynamodb.Table('estec-backend-alpha-RawSensorData')
# factory_id = 'F_xGc676J6PH'
# mapping_datetime= {
#         "hiện tại": 0,
#         "ngay bây giờ": 0,
#         "lúc này": 0,
#         "hôm nay": 0,
#         "hôm qua": -1,
#         "hôm kia": -2,
#         "ngày mai": 1,
#         "hôm trước": -1,
#     }
# keyword_datetime = list(mapping_datetime.keys())

# def decimal_default(obj):
#     if isinstance(obj, Decimal):
#         return float(obj)
#     raise TypeError

# def get_current_datetime(offset_date=0):
#     now = datetime.utcnow() + timedelta(hours=6, minutes=59, days=offset_date) 
#     current_date = now.strftime("%Y-%m-%d")
#     current_time = now.strftime("%H:%M:00")
#     return current_date, current_time

# def check_keyword_now(input_text: str, parameters: list) -> tuple:
#     date = None
#     time = None
#     for kw in keyword_datetime:
#         if kw in input_text:
#             logger.info('check_keyword_now (date): %s', kw)
#             date, time = get_current_datetime(mapping_datetime[kw])
#     logger.info('Final check_keyword_now: date=%s, time=%s', date, time)
#     return date, time

# def query_data_dynamodb_variables(factory_id_date_prefix: str, time: str, columns=None):
#     if columns:
#         logger.info('query_dynamodb_variables function')
#         logger.info('columns: %s', columns)
#         expression_attribute_names = {}
#         projection_expression_parts = []
#         columns.append('Date')
#         columns.append('Time')
#         for i, col in enumerate(columns):
#             alias = f"#col{i}"
#             expression_attribute_names[alias] = col
#             projection_expression_parts.append(alias)
#         projection_expression = ", ".join(projection_expression_parts)
#         logger.info('projection_expression: %s', projection_expression)
#         logger.info('expression_attribute_names: %s', expression_attribute_names)
#         response = table.query(
#             KeyConditionExpression=Key('FactoryId_Date').eq(factory_id_date_prefix) & Key('Time').eq(time),
#             ProjectionExpression=projection_expression,
#             ExpressionAttributeNames=expression_attribute_names,
#             ScanIndexForward=False,
#             Limit=1
#         )
#     else:
#         response = table.query(
#             KeyConditionExpression=Key('FactoryId_Date').eq(factory_id_date_prefix) & Key('Time').eq(time),
#             ScanIndexForward=False,
#             Limit=1
#         )
#     items = response.get('Items', [])
#     return items[0] if items else None

# def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
#     try:
#         start_time = datetime.now()
#         logger.info('event: %s', event)
#         action_group = event['actionGroup']
#         function = event.get('function', '')
#         apiPath = event.get('apiPath', '')
#         httpMethod = event.get('httpMethod', '')
#         message_version = event.get('messageVersion', 1)
#         parameters = event['requestBody']['content']['application/json']['properties']
#         param_dict = {param['name']: param['value'] for param in parameters}
#         input_text = event.get('inputText', '').lower()
#         logger.info('inputText: %s', input_text)
#         logger.info('parameters: %s', parameters)

#         session_attributes = event.get("sessionAttributes", {})
#         logger.info('session_attributes: %s', session_attributes)
#         connection_id = session_attributes.get("connection_id", "")
#         requestId = session_attributes.get("request_id", "")
#         action = session_attributes.get("action", "sendMessage")
#         logger.info('connection_id: %s', connection_id)
#         logger.info('requestId: %s', requestId)
#         logger.info('action: %s', action)

#         if apiPath=='/query_data':
#             date, time = check_keyword_now(input_text, parameters)
            
#             date_list = []
#             time_list = []
#             date_list.append(date)
#             time_list.append(time)

#             date_raw = next((item['value'] for item in parameters if item['name'] == 'date'), None)
#             if date_raw:
#                 date_raw = [date.strip().strip('"') for date in date_raw.strip('[]').split(',')] if date_raw else None
#                 logger.info('date_raw: %s', date_raw)
#                 for date in date_raw:
#                     date_list.append(date)
#             logger.info('date_list: %s', date_list)

#             time_raw = next((item['value'] for item in parameters if item['name'] == 'time'), None)
#             if time_raw:
#                 time_raw = [time.strip().strip('"') for time in time_raw.strip('[]').split(',')] if time_raw else None
#                 logger.info('time_raw: %s', time_raw)
#                 for time in time_raw:
#                     time_list.append(time)
            
#             date_list = [date for date in date_list if date is not None]
#             time_list = [time for time in time_list if time is not None]
#             logger.info('time_list: %s', time_list)
#             max_len = max(len(date_list), len(time_list))
#             if len(date_list) < max_len:
#                 date_list += [date_list[0]] * (max_len - len(date_list))
#             if len(time_list) < max_len:
#                 time_list += [time_list[0]] * (max_len - len(time_list))

#             logger.info('date_list: %s', date_list)
#             logger.info('time_list: %s', time_list)

#             result_query = []

#             for i in range(len(date_list)):
#                 date = date_list[i]
#                 time = time_list[i]
#                 factory_id_date_prefix = f"{factory_id}::{date}"
#                 columns_str = param_dict.get('columns', [])
#                 columns = [col.strip().strip('"') for col in columns_str.strip('[]').split(',')] if columns_str else None
#                 logger.info('factory_id_date_prefix: %s', factory_id_date_prefix)
#                 logger.info('time: %s', time)
#                 logger.info('columns: %s', columns)
#                 item = query_data_dynamodb_variables(factory_id_date_prefix, time, columns)
#                 if item:
#                     result_query.append(item)
            
#             logger.info('result_query: %s', result_query)

#             finalresponse = bedrock.invoke_model(
#                 body=json.dumps(
#                     {
#                     "anthropic_version": "bedrock-2023-05-31",
#                     "max_tokens": 200,
#                     "top_k": 250,
#                     "stop_sequences": [],
#                     "temperature": 1,
#                     "top_p": 0.999,
#                     "messages": [
#                         {
#                             "role": "user",
#                             "content": [
#                                 {
#                                     "type": "text",
#                                     "text": f"Trả lời câu hỏi dựa trên dữ liệu được cung cấp:\n{json.dumps(result_query, indent=2, ensure_ascii=False, default=decimal_default)}\n\nCâu hỏi: {input_text}\n\nTrả lời:"
#                                 }
#                             ]
#                         }
#                     ]
#                 }),
#                 modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
#                 accept="application/json",
#                 contentType="application/json"
#             )
#             finalresponse_body = json.loads(finalresponse['body'].read().decode('utf-8'))
#             finalresponse = finalresponse_body['content'][0]['text']
#             urls = re.findall(r'(https?://[^\s]+)', finalresponse)
#             url = urls[-1] if urls else None
            
#             websocket_client.post_to_connection(
#                 ConnectionId=connection_id,
#                 Data=json.dumps({
#                     "statusCode" : 200,
#                     "action": action,
#                     "response": finalresponse,
#                     "requestId": requestId,
#                     "url": url
#                 })
#             )

#             end_time = datetime.now()
#             logger.info('Time: %s', end_time - start_time)
#             logger.info('finalresponse_body: %s', finalresponse_body)

#             # body = f"Dữ liệu truy vấn từ DynamoDB:\n{json.dumps(result_query, indent=2, ensure_ascii=False, default=decimal_default)}"
#         # elif apiPath=='/analysis_data':
#         #     body = f"Chức năng đang được phát triển"

#         # response_body = {
#         #     'TEXT': {
#         #         'body': body
#         #     }
#         # }

#         response_body = {}
#         action_response = {
#             'actionGroup': action_group,
#             'responseBody': response_body,
#             'httpMethod': httpMethod,
#             'apiPath': apiPath
#         }
#         response = {
#             'response': action_response,
#             'messageVersion': message_version
#         }

#         logger.info('Response: %s', response)
#         return response

#     except KeyError as e:
#         logger.error('Missing required field: %s', str(e))
#         return {
#             'statusCode': HTTPStatus.BAD_REQUEST,
#             'body': f'Error: {str(e)}'
#         }
#     except Exception as e:
#         logger.error('Unexpected error: %s', str(e))
#         return {
#             'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
#             'body': 'Internal server error'
#         }
