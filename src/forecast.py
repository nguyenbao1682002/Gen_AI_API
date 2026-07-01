import json
import boto3
import io
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from urllib.parse import quote
import os
from boto3.dynamodb.conditions import Key
from prophet import Prophet

def query_all_items(table, **kwargs):
    items = []
    while True:
        response = table.query(**kwargs)
        items.extend(response['Items'])
        if 'LastEvaluatedKey' in response:
            kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break
    return items

def forecast_function(input_data, dynamodb, s3, prefix_s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET):
    try:
        body = input_data
        sensor_ids = body['sensor_ids']
        print("sensor_ids:", sensor_ids)
        start_time = body['start_time']
        start_time = datetime.fromisoformat(start_time)
        end_time = body['end_time']
        end_time = datetime.fromisoformat(end_time)
        if start_time > end_time:
            start_time, end_time = end_time, start_time
        start_date = start_time.date()
        end_date = end_time.date()
        start_time = start_time.time()
        end_time = end_time.time()
        aggregation = body.get('aggregation', 'raw')
        factory_id = body.get('factory_id', 'F_xGc676J6PH')

        results = {}
        table = dynamodb.Table(DYNAMODB_TABLE)

        columns = []
        columns.append('Date')
        columns.append('Time')

        expression_attribute_names = {}
        projection_expression_parts = []
        for sensor_id in sensor_ids:
            columns.append(f"{sensor_id}")
        for i, col in enumerate(columns):
            alias = f"#col{i}"
            expression_attribute_names[alias] = col
            projection_expression_parts.append(alias)
        projection_expression = ", ".join(projection_expression_parts)
        # print("projection_expression:", projection_expression)
        # print("expression_attribute_names:", expression_attribute_names)
        # print(start_date, end_date)
        # print(start_time, end_time)
        # Query DynamoDB
        query_data = []
        date_list = pd.date_range(start=start_date, end=end_date).date
        print("date_list:", date_list)
        for date in date_list:
            # factory_id_date_prefix = f"{factory_id}::{date.isoformat()}"
            factory_id_date_prefix = f"{factory_id}:{date.isoformat()}"
            print("factory_id_date_prefix:", factory_id_date_prefix)
            print("start_time:", start_time.isoformat())
            print("end_time:", end_time.isoformat())
            query_args = {
                'KeyConditionExpression': Key('FactoryId_Date').eq(factory_id_date_prefix) &
                                        Key('Time').between(start_time.isoformat(), end_time.isoformat()),
                'ProjectionExpression': projection_expression,
                'ExpressionAttributeNames': expression_attribute_names,
                'ScanIndexForward': False
            }
            items = query_all_items(table, **query_args)
            # print("items:", items)
        
            for item in items:
                item['Date'] = date.isoformat()
                item['Time'] = item['Time']
                query_data.append(item)

        df = pd.DataFrame(query_data)
        print("df:", df.head(2))
        print("df:", df.tail(2))
        df['timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df.drop(columns=['Date', 'Time'], inplace=True)

        valid_sensor_ids = []
        for sensor_id in sensor_ids:
            if sensor_id in df.columns:
                df[sensor_id] = pd.to_numeric(df[sensor_id], errors='coerce')
                valid_sensor_ids.append(sensor_id)
            
        df.set_index('timestamp', inplace=True)
        df = df.sort_index(ascending=True)
        # print("df:", df)
        df = df.ffill()
        
        # Aggregation
        freq_map = {
            'raw': None,
            'hourly': 'H',
            'daily': 'D',
            'monthly': 'M',
            'yearly': 'Y'
        }
        freq = freq_map.get(aggregation)
        if freq:
            df = df.resample(freq).mean()

        # --------- THÊM PHẦN PROPHET -------------
        horizon_map = {
            'raw': 60,
            'hourly': 24,
            'daily': 7,
            'monthly': 12,
            'yearly': 5
        }
        forecast_horizon = horizon_map.get(aggregation, 60)
        forecast_frames = []
        for sensor_id in valid_sensor_ids:
            # Chuẩn bị dữ liệu cho Prophet
            sensor_df = df[[sensor_id]].reset_index().rename(
                columns={'timestamp': 'ds', sensor_id: 'y'}
            )
            model = Prophet()
            model.fit(sensor_df)

            # Tạo khung thời gian mới để dự báo
            prophet_freq_map = {
                'raw': 'min',
                'hourly': 'H',
                'daily': 'D',
                'monthly': 'MS',   # Prophet: start of month
                'yearly': 'Y'
            }
            prophet_freq = prophet_freq_map.get(aggregation, 'min')
            future = model.make_future_dataframe(periods=forecast_horizon, freq=prophet_freq)

            forecast = model.predict(future)
            forecast['sensor_id'] = sensor_id
            forecast_frames.append(
                forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'sensor_id']]
            )
        # Gộp forecast
        forecast_df = pd.concat(forecast_frames)
        forecast_df.set_index('ds', inplace=True)

        # Plotting
        plt.figure(figsize=(14, 6))
        
        for column in df.columns:
            plt.plot(df.index, df[column], label=column)

        # Dự báo
        for sensor_id in valid_sensor_ids:
            forecast = forecast_df[forecast_df['sensor_id'] == sensor_id]
            plt.plot(
                forecast.index,
                forecast['yhat'],
                linestyle='--',
                label=f"{sensor_id} - forecast"
            )
            plt.fill_between(
                forecast.index,
                forecast['yhat_lower'],
                forecast['yhat_upper'],
                alpha=0.3,
                label=f"{sensor_id} - bound"
            )

        plt.title(f"Biểu đồ cảm biến từ {start_date} đến {end_date}")
        plt.xlabel(f"Thời gian từ {start_date} đến {end_date}")
        plt.ylabel("Giá trị / Value")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        file_name = f"{prefix_s3}/dashboard_{aggregation}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        s3.put_object(Bucket=S3_BUCKET, Key=file_name, Body=buf, ContentType='image/png')
        plot_url = f"https://{S3_BUCKET}.s3.{REGION_S3_BUCKET}.amazonaws.com/{quote(file_name)}"
        plt.close()

        # Trích xuất chuỗi truy vấn data tóm tắt (để agent xử lý)
        data_summary = df.describe().to_dict()

        results = {
            "plot_url": plot_url,
            "data_query": json.dumps(data_summary),
            "dataframe": df.to_dict(orient='records'),
            "action": "plotdashboard"
        }

        return {
            "statusCode": 200,
            "body": json.dumps(results),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                "Content-Type": "application/json"
            }
        }
