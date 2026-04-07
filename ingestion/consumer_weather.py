import json
from kafka import KafkaConsumer
import pandas as pd
from db.postgresConnection import get_engine

engine = get_engine()
consumer = KafkaConsumer(
    'weather_topic',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)
print("Consuming weather data...")
for message in consumer:
    row = message.value
    df = pd.DataFrame([row])
    df.to_sql(
        "weather_stream_bronze",
        engine,
        if_exists="append",
        index=False
    )