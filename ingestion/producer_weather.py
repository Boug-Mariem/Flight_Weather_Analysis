import pandas as pd
import json
import time
from kafka import KafkaProducer
import numpy as np
from datetime import date, datetime


def clean_for_json(record):
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, (pd.Timestamp, datetime, date)):
            cleaned[k] = v.isoformat()
        elif isinstance(v, (np.generic,)):
            cleaned[k] = v.item()
        elif pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def stream_weather_to_kafka(file_path, flights_date):
    df = pd.read_csv(file_path)
    df["time"] = pd.to_datetime(df["time"]).dt.date
    future_dates = sorted(df[df["time"] > flights_date]["time"].unique())
    if not future_dates:
        return
    next_date = future_dates[0]
    df_stream = df[df["time"] == next_date]

    print("Sending weather data to Kafka...")
    for _, row in df_stream.iterrows():
        message = clean_for_json(row.to_dict())
        producer.send("weather_topic", value=message)
        time.sleep(0.05)
    producer.flush()
    return next_date