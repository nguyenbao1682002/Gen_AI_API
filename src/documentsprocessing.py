import tempfile
from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR
from sentence_transformers import SentenceTransformer
import boto3
import uuid
import json

# Khởi tạo OCR và model embedding
ocr = PaddleOCR(use_angle_cls=True, lang='en')
embedder = SentenceTransformer("all-MiniLM-L6-v2")  # hoặc model phù hợp với bạn

def pdf2s3vector_function(file, dynamodb, s3, table_name, bucket_name, region):
    try:
        # Bước 1: Đọc PDF dạng ảnh
        pdf_bytes = file.file.read()
        images = convert_from_bytes(pdf_bytes)

        full_text = ""
        for image in images:
            result = ocr.ocr(image)
            for line in result:
                for box in line:
                    text = box[1][0]
                    full_text += text + " "

        if not full_text.strip():
            return {"error": "OCR không phát hiện được văn bản nào."}

        # Bước 2: Tạo embedding
        embedding = embedder.encode(full_text)

        # Bước 3: Upload lên S3 Vector Bucket
        object_id = str(uuid.uuid4())

        s3_key = f'vector_data/{object_id}.json'
        s3_body = json.dumps({
            "id": object_id,
            "text": full_text,
            "vector": embedding.tolist()
        })

        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=s3_body,
            ContentType='application/json'
        )

        # (Tuỳ chọn) Ghi thông tin vào DynamoDB
        dynamodb.put_item(
            TableName=table_name,
            Item={
                'id': {'S': object_id},
                's3_key': {'S': s3_key},
                'region': {'S': region},
                'text': {'S': full_text[:500]}  # tóm tắt
            }
        )

        return {"message": "PDF processed and vector uploaded successfully.", "id": object_id}

    except Exception as e:
        return {"error": str(e)}
