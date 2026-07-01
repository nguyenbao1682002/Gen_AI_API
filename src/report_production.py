from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os
import boto3
from boto3.dynamodb.conditions import Key
from urllib.parse import quote
import json

STT_MAP = {
    "ĐÁ VÔI KHAI THÁC": 1,
    "LATARITE": 2,
    "BÓC TẦNG PHỦ": 3,
    "PHI NGUYÊN LIỆU": 4,
    "KHOAN": 5,
    "VẬT LIỆU NỔ": 6
}

class PDF(FPDF):
    def table(self, data):
        self.set_font("Serif", "", 9)
        col_widths = [10, 75, 15, 25, 30, 30, 30, 30, 25]
        for row in data[:]:
            for i, item in enumerate(row):
                if i == 0:
                    if item in ["1", "2", "3", "4", "5", "6"]:
                        self.set_font("Serif", "B", 12)
                        self.cell(col_widths[i], 8, item, border="LTR", align="C")
                    else:
                        self.set_font("Serif", "B", 12)
                        self.cell(col_widths[i], 8, item, border="LR", align="C")
                elif i == 1:
                    self.set_font("Serif", "", 10)
                    self.cell(col_widths[i], 8, item, border=1, align="L")
                else:
                    self.set_font("Serif", "B", 10)
                    self.cell(col_widths[i], 8, item, border=1, align="C")
            self.ln()
            if row == data[-1]:
                self.cell(sum(col_widths), 0, "", border="T")

def format_vn_number(value):
    try:
        number = float(value)
        if number == 0:
            return "-"
        else:
            return "{:,.2f}".format(number).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

def reportproduction_PD1KT(input_data, dynamodb, s3, prefix_s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET):
    body = input_data
    now = (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%S")
    date_time_str = body.get('datetime', now)
    date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M:%S")
    print("date_time:", date_time)
    type_report = body.get('type_report', 'daily')
    print("type_report:", type_report)
    factory_id = body.get('factory_id', 'F_xGc676J6PH')
    print("factory_id:", factory_id)
    area = body.get('type', 'PD1KT')
    print("area:", area)
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    pdf = PDF(orientation="L")
    pdf.add_font("Serif", "", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")
    pdf.add_font("Serif", "B", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf")
    pdf.set_font("Serif", "", 12)
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.image("./images/logo.png", x=12, y=12, w=75)
    pdf.set_font("Serif", "B", 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "NHÀ MÁY XI MĂNG BÌNH PHƯỚC", align="C")
    pdf.ln(10)
    pdf.cell(0, 10, "XƯỞNG KHAI THÁC", align="C")
    pdf.ln(10)
    pdf.set_font("Serif", "B", 18)
    pdf.set_text_color(223, 126, 30)
    pdf.cell(0, 10, "BÁO CÁO SẢN XUẤT", align="C")
    pdf.ln(10)

    date_prefix = date_time.strftime("%Y-%m-%d")
    factory_id_date_prefix = f"{factory_id}:{date_prefix}"
    print("factory_id_date_prefix:", factory_id_date_prefix)

    date = date_time.strftime(f"Ngày %d tháng %m năm %Y")
    pdf.set_font("Serif", "B", 12)
    pdf.set_text_color(255, 0, 0)
    pdf.cell(0, 10, date, align="R")
    pdf.ln(10)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Serif", "B", 14)
    pdf.cell(0, 10, "I. PHÂN ĐOẠN 1: KHAI THÁC", align="L")
    pdf.ln(10)

    pdf.set_fill_color(200, 255, 255)
    pdf.set_font("Serif", "B", 10)
    pdf.cell(10, 20, "STT", border=1, align="C", fill=True)
    pdf.cell(75, 20, "NGUYÊN LIỆU", border=1, align="C", fill=True)
    pdf.cell(15, 20, "ĐVT", border=1, align="C", fill=True)
    pdf.cell(25, 20, "TỒN ĐẦU KỲ", border=1, align="C", fill=True)
    pdf.cell(60, 10, "NHẬP", border=1, align="C", fill=True)
    pdf.cell(60, 10, "XUẤT", border=1, align="C", fill=True)
    pdf.cell(25, 20, "TỒN CUỐI KỲ", border=1, align="C", fill=True)
    pdf.ln(10)

    pdf.cell(10, 10, "", border="LBR")
    pdf.cell(75, 10, "", border="LBR")
    pdf.cell(15, 10, "", border="LBR")
    pdf.cell(25, 10, "", border="LBR")

    for title in ["TRONG NGÀY", "LŨY KẾ THÁNG"]:
        pdf.cell(30, 10, title, border=1, align="C", fill=True)
    for title in ["TRONG NGÀY", "LŨY KẾ THÁNG"]:
        pdf.cell(30, 10, title, border=1, align="C", fill=True)
    pdf.cell(25, 10, "", border="LBR")
    pdf.ln(10)

    date_now = (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d")
    if date_prefix == date_now:
        time = (datetime.now() + timedelta(hours=7)).strftime("%H:%M:00")
    else:
        time = "23:59:00"
    
    print("time checked:", time)
    response = table.query(
        KeyConditionExpression= Key("FactoryId_Date").eq (factory_id_date_prefix) & Key("Time").eq(time),
        ScanIndexForward=False,
        Limit=1
    )
    items = response.get("Items", [])
    # print("items:", items)
    if items:
        items = items[0]

    with open("./json_data/PD1KT.json", "r", encoding="utf-8") as f:
        PD1KT = json.load(f)
    with open("./json_data/PD1KT_Unit.json", "r", encoding="utf-8") as f:
        PD1KT_Unit = json.load(f)
    PD1KT_table = []

    for key, value in PD1KT.items():
        STT = STT_MAP.get(value, '')
        PD1KT_table.append([
            str(STT),
            value,
            PD1KT_Unit[key],
            format_vn_number(items.get(f"PXKT_{key}_TON_DAU", '-')),
            format_vn_number(items.get(f"PXKT_{key}_NHAP", '-')),
            format_vn_number(items.get(f"PXKT_{key}_LK_THANG_NHAP", '-')),
            format_vn_number(items.get(f"PXKT_{key}_XUAT", '-')),
            format_vn_number(items.get(f"PXKT_{key}_LK_THANG_XUAT", '-')),
            format_vn_number(items.get(f"PXKT_{key}_TON_CUOI", '-'))])

    pdf.table(PD1KT_table)
    # file log pdf for dev
    pdf.output(f"./localstorage/baocaosanxuat{date_prefix}.pdf")

    with open(f"./localstorage/baocaosanxuat{date_prefix}.pdf", 'rb') as f:
        pdf_data = f.read()

    file_name = f"{prefix_s3}/report{area}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=file_name,
        Body=pdf_data,
        ContentType='application/pdf'
    )
    report_url = f"https://{S3_BUCKET}.s3.{REGION_S3_BUCKET}.amazonaws.com/{quote(file_name)}"

    results = {
            "report_url": report_url
        }
        
    return {
            "statusCode": 200,
            "body": json.dumps(results),
            "headers": {
                "Content-Type": "application/json"
            }
        }
