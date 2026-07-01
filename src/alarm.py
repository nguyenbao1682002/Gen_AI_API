from datetime import datetime, timedelta
import uuid
import pytz
import pandas as pd
from boto3.dynamodb.conditions import Key
import boto3

def query_all_items(table, **kwargs):
    items = []
    while True:
        response = table.query(**kwargs)
        items.extend(response.get('Items', []))
        if 'LastEvaluatedKey' in response:
            kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break
    return items

def alarm(input_data, dynamodb, s3, DYNAMODB_TABLE, S3_BUCKET, REGION_S3_BUCKET):
    factory_id = input_data.get('factory_id', 'F_xGc676J6PH')
    date_time_str = input_data.get('datetime', datetime.now().strftime("%Y-%m-%dT%H:%M:00"))
    date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M:00")
    date = date_time.strftime("%Y-%m-%d")
    factory_id_date_prefix = f"{factory_id}:{date}"
    end_time = date_time.strftime("%H:%M:00")
    start_time = (date_time - pd.Timedelta(minutes=59)).strftime("%H:%M:00")

    print("factory_id_date_prefix:", factory_id_date_prefix)
    print("start_time:", start_time)
    print("end_time:", end_time)

    table = dynamodb.Table(DYNAMODB_TABLE)

    columns = [
        "Date", "Time", "Ratio_PC", "4G1FN01DRV01_M1001_SI", "Kilnfeed_SP_Total", "4G1GA03XAC01_O2", "Result_AHC", "4K1KP01KHE01_B8701", "BZTL",
        "PC_coal_Setpt", "4R1GQ01JNT01_T8201", "SZ_coal_Setpt", "4G1GA02XAC01_O2", "4K1KP01DRV01_M2001_EI", "41KP01DRV01_SP", "4K1KP01DRV01_Speed",
        "4G1PS01GPJ02_T8201", "4G1GA01XAC01_O2", "4G1KJ01JST00_T8401", "_G1PJ01MCH02T8201_TIA.IO.Signal.Value", "Actual_KF", "4G1GA01XAC01_NO",
        "BP_KSCL_CL_CaOf", "BP_KSCL_CL_SO3", "4S1FN01DRV01_M2001_EI", "4K1KP01KHE01_B5001", "4S1GP01JST00_T8104", "4E1FN01TVJ01_PID_MV",
        "4E1GP01JST00_B5002", "4C1DD02DDJ01_M5501_MV", "Actual_coal_PC", "CW1RB01JST00_B5001", "Actual_coal_SZ", "CW1RB02JST00_B5001",
        "_L72BW01_W01", "4G1PS02PGP02_T8201", "4G1PS03PGP02_T8201", "Grate_Hyd_Pressure", "_4C1BE01DRV01_M2001.Current.Value",
        "_4C1BE01DRV02_M2001.Current.Value", "4C1BE01DRV01_M2001_I", "4G1PS02PGP01_T8201",
        "4G1PS01GPJ01_T8201I", "4G1GA01XAC01_CO", "4G1GA02XAC01_A0901", "4G1GA03XAC01_A0901", "4G1GA04XAC01_A0901", "4G1FN01MMS01_T9601_MV1",
        "4G1KJ01JST00_B5001", "4R1RR01EXD01_T8102", "4S1GP02JST00_T8201", "4T1AY01JST00_B8702", "4R1FN01TVJ01_B5101_INFSC", "4R1GQ01HYS01_T8101",
        "4C1BF01FNJ01_M2001_I", "4G1GA04XAC01_O2", "4K1KP01RST01_T8101", "4K1KP01RST01_T8102", "4K1KP01RST01_T8103", "4K1KP01RST01_T8104",
        "4K1KP01RST02_T8101", "4K1KP01RST02_T8102", "4K1KP01RST02_T8103", "4K1KP01RST02_T8104", "4R1FC02TVJ01B5101_INFS", "4R1FC06TVJ01B5101_INFS",
        "4E1GP01JST00_T8202"]

    items = query_all_items(
        table,
        KeyConditionExpression=Key("FactoryId_Date").eq(factory_id_date_prefix) & Key("Time").between(start_time, end_time),
        ScanIndexForward=False,
        Limit=60
    )
    # items = response.get("Items", [])
    df = pd.DataFrame(items)
    df_alarm = df[columns]

    if not items:
        return {"error": "No data available for the specified time range."}
    print("df_alarm:", df_alarm)
    response_reminder = check_reminder(df_alarm)
    return response_reminder

def check_reminder(row):
    if row is None or row.empty:
        return ["No data available"]

    response_reminder = []

    conditions = [
        (
            abs(row["4G1PS02PGP01_T8201"].iloc[0] - row["4G1PS02PGP02_T8201"].iloc[0]) > 10,
            "Kiểm tra, vệ sinh trám mái úp - đầu lò", 
            "Nhiệt outlet C2", 
            "(4G1PS02PGP01_T8201-4G1PS02PGP02_T8201) > 10"),

        (
            row["4G1PS02PGP01_T8201"].iloc[0] > 775 or row["4G1PS02PGP02_T8201"].iloc[0] > 775,
            "Giảm nhiệt tháp - nguy cơ bám dính Nhiệt outlet C2", 
            "Nhiệt outlet C2", 
            "4G1PS02PGP01_T8201 > 775, 4G1PS02PGP02_T8201 > 775"),

        (
            row["4G1PS01GPJ01_T8201I"].iloc[0] > 875,
            "Giảm nhiệt tháp - nguy cơ bám dính Nhiệt outlet C1", 
            "Nhiệt outlet C1", 
            "4G1PS01GPJ01_T8201I > 875"),

        (
            row["4G1PS01GPJ01_T8201I"].iloc[0] < 810,
            "Đo nhiệt báo sai, kiểm tra", 
            "Nhiệt outlet C1", 
            "4G1PS01GPJ01_T8201I < 810"),

        (
            any([
                row["4G1GA01XAC01_CO"].iloc[0] > 0.25,
                row["4G1GA02XAC01_A0901"].iloc[0] > 0.25,
                row["4G1GA03XAC01_A0901"].iloc[0] > 0.25,
                row["4G1GA04XAC01_A0901"].iloc[0] > 0.25
            ]), 
            "Cẩn thận CO hệ thống", 
            "Hệ thống phân tích khí Ga01,2,3,4", 
            "4G1GA01XAC01_CO > 0.25, 4G1GA02XAC01_A0901 > 0.25, 4G1GA03XAC01_A0901 > 0.25, 4G1GA04XAC01_A0901 > 0.25"),

        (
            row["4G1FN01MMS01_T9601_MV1"].iloc[0] > 4.5,
            "Idfan rung cao, cần xử lý", 
            "Quạt ID", 
            "4G1FN01MMS01_T9601_MV1 > 4.5"),

        (
            row["4G1KJ01JST00_T8401"].iloc[0] < 1000,
            "Đo nhiệt độ đầu lò sai", 
            "Đầu lò", 
            "4G1KJ01JST00_T8401 < 1000"),

        (
            row["4G1KJ01JST00_B5001"].iloc[0] < -8,
            "Vệ sinh trám đầu lò", 
            "Đầu lò", 
            "4G1KJ01JST00_B5001 < -8"),

        (
            row["4G1GA01XAC01_O2"].iloc[0] > 6,
            "Phân tích khí GA01 không chính xác", 
            "Đầu lò", 
            "4G1GA01XAC01_O2 > 6"),

        (
            row["4K1KP01DRV01_M2001_EI"].iloc[0] > 380,
            "Tải lò cao, kiểm tra tình trạng động cơ chính lò", 
            "Lò nung", 
            "4K1KP01DRV01_M2001_EI > 380"),

        (
            row["BP_KSCL_CL_CaOf"].iloc[0] < 0.8 and row["BP_KSCL_CL_CaOf"].iloc[59] < 0.8,
            "Điều chỉnh nâng CaOf, nguy cơ bám trám lò", 
            "Cooler", 
            "BP_KSCL_CL_CaOf < 0.8"),

        (
            row["BP_KSCL_CL_CaOf"].iloc[0] > 2,
            "CaOf cao, chú ý chuyển silo phụ", 
            "Cooler", 
            "BP_KSCL_CL_CaOf > 2"),

        (
            row["BP_KSCL_CL_SO3"].iloc[0] > 1.4,
            "Lò thiếu gió", 
            "Cooler", 
            "BP_KSCL_CL_SO3 > 1.4"),

        (
            row["4R1RR01EXD01_T8102"].iloc[0] > 85,
            "Nhiệt búa cooler cao", 
            "Cooler", 
            "4R1RR01EXD01_T8102 > 85"),

        (
            row["4S1GP02JST00_T8201"].iloc[0] < 260,
            "Nhiệt khí thải cooler thấp", 
            "Cooler", 
            "4S1GP02JST00_T8201 < 260"),

        (
            row["4T1AY01JST00_B8702"].iloc[0] > 120,
            "Nhiệt clinker cao, điều chỉnh giảm nhiệt clinker", 
            "Cooler", 
            "4T1AY01JST00_B8702 > 120"),

        (
            row["4T1AY01JST00_B8702"].iloc[0] < 100,
            "Nhiệt clinker thấp, điều chỉnh giảm quạt cooler", 
            "Cooler", 
            "4T1AY01JST00_B8702 < 100"),

        (
            (row["4R1FN01TVJ01_B5101_INFSC"].iloc[1] - row["4R1FN01TVJ01_B5101_INFSC"].iloc[0]) > 2500,
            "Giảm tốc độ lò nhanh, quá tải cooler-búa", 
            "Cooler", 
            "4R1FN01TVJ01_B5101_INFSC > 0.5"),

        (
            row["4R1GQ01HYS01_T8101"].iloc[0] > 50.5,
            "Vệ sinh lọc nước làm mát thủy lực cooler", 
            "Cooler", 
            "4R1GQ01HYS01_T8101 > 50.5"),
        
        (
            row["4C1BF01FNJ01_M2001_I"].iloc[0] < 8,
            "Kiểm tra ống hút lọc bụi, kiểm tra van màn lọc bụi",
            "Rawmeal Silo",
            "4C1BF01FNJ01_M2001_I < 8"),

        (
            row["Grate_Hyd_Pressure"].iloc[0] > 180,
            "Chú ý quá tải cooler, giảm sâu tốc độ lò",
            "Cooler",
            "Grate_Hyd_Pressure > 180"),
        
        (
            row["4G1GA02XAC01_O2"].iloc[0] < 2 and row["4G1GA03XAC01_O2"].iloc[0] < 2 and row["4G1GA04XAC01_O2"].iloc[0] < 2,
            "Oxi các GA thấp, nguy cơ thiếu gió hệ thống",
            "Hệ thống phân tích khí GA02,3,4",
            "4G1GA02XAC01_O2 < 2, 4G1GA03XAC01_O2 < 2, 4G1GA04XAC01_O2 < 2"),

        (
            row["4K1KP01RST01_T8101"].iloc[0] > 55 and row["4K1KP01RST01_T8102"].iloc[0] > 55 and row["4K1KP01RST01_T8103"].iloc[0] > 55 and row["4K1KP01RST01_T8104"].iloc[0] > 55
            and row["4K1KP01RST02_T8101"].iloc[0] > 55 and row["4K1KP01RST02_T8102"].iloc[0] > 55 and row["4K1KP01RST02_T8103"].iloc[0] > 55 and row["4K1KP01RST02_T8104"].iloc[0] > 55,
            "Kiểm tra nước làm mát, hệ thống tự lựa",
            "Lò Nung",
            "4K1KP01RST01_T8101 > 55, 4K1KP01RST01_T8102 > 55, 4K1KP01RST01_T8103 > 55, 4K1KP01RST01_T8104 > 55, 4K1KP01RST02_T8101 > 55, 4K1KP01RST02_T8102 > 55, 4K1KP01RST02_T8103 > 55, 4K1KP01RST02_T8104 > 55"),

        (
            row["4R1FC02TVJ01B5101_INFS"].iloc[0] < 26500,
            "Kiểm tra lại ghi tĩnh của 4R1FC02TVJ01B5101_INFS",
            "Cooler",
            "4R1FC02TVJ01B5101_INFS < 26500"),
        
        (
            row["4R1FC06TVJ01B5101_INFS"].iloc[0] < 50000,
            "Kiểm tra lại ghi tĩnh của 4R1FC06TVJ01B5101_INFS",
            "Cooler",
            "4R1FC06TVJ01B5101_INFS < 50000"),
    ]
    # current_date_time = new_time.strftime("%d-%m-%Y - %I:%M %p")

    for condition, reminder, zone, logic in conditions:
        if condition:
            schema = {
                "logic": logic,
                "description": reminder,
                "target": zone,
                "datetime": datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))
            }
            response_reminder.append(schema)
    print("response_reminder:", response_reminder)
    return response_reminder