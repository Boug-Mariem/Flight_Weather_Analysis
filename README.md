# Flight Delay & Weather Data Engineering Pipeline

## Project Description
This project is an end-to-end data engineering pipeline designed to analyze and predict flight delays based on weather conditions.
It processes flight data and meteorological data to:
- understand the impact of weather on flight delays
- build analytical aggregations (airports, airlines, weather conditions)
- generate insights through dashboards
- provide a basic delay prediction module
The system follows a Medallion Architecture (Bronze → Silver → Gold) and integrates both batch and streaming processing.

## Use Case
The main goal is to answer:
How do weather conditions affect flight delays, and which airports/airlines perform best under different conditions?
Additionally, the system provides:
- operational insights (airport & airline performance)
- temporal analysis (seasonal/monthly trends)
- predictive estimation of flight delays

## Architecture

```text
                +----------------------+
                |   Kaggle Datasets    |
                | (Flights + Weather)  |
                +----------+-----------+
                           |
        +------------------+------------------+
        |                                     |
  Batch Ingestion                      Kafka Streaming
  (Flights Data)                     (Weather Data)
        |                                     |
        +------------------+------------------+
                           |
                 +---------v---------+
                 |   Bronze Layer     |
                 | Raw Data Storage   |
                 | (PostgreSQL)      |
                 +---------+---------+
                           |
                 +---------v---------+
                 |   Silver Layer     |
                 | Cleaning &        |
                 | Standardization   |
                 +---------+---------+
                           |
                 +---------v---------+
                 |    Gold Layer      |
                 | Feature Engineering|
                 | & Joins           |
                 +---------+---------+
                           |
        +------------------+------------------+
        |                                     |
 Aggregation Tables                Prediction Module
 (Weather / Airport /            (Delay Estimation)
  Airline Analysis)
                           |
                 +---------v---------+
                 | Streamlit Dashboard|
                 | Data Visualization |
                 +-------------------+
```
## Data Sources
_Flight Data_ :
US Civil Flights 2023 (Kaggle) (https://www.kaggle.com/datasets/bordanova/2023-us-civil-flights-delay-meteo-and-aircraft/data?select=US_flights_2023.csv)  

_Weather Data_ :
Meteorological dataset 2023 (Kaggle) (https://www.kaggle.com/datasets/bordanova/2023-us-civil-flights-delay-meteo-and-aircraft/data?select=weather_meteo_by_airport.csv)

## Tech Stack
**Core Technologies**  

Python → main processing language  

Pandas / NumPy → data transformation  

PostgreSQL → data warehouse storage  

Chosen for:  
- relational modeling (joins between flights & weather)
- strong SQL analytical performance
- simplicity and integration with Python

**Streaming**
Apache Kafka  

Used for:
- simulating real-time weather ingestion
- decoupling producer and consumer
- building scalable streaming architecture

**Orchestration**  
Apache Airflow  

Used for:
- DAG-based pipeline orchestration
- scheduling batch processing
- monitoring and retry mechanisms

**Visualization**  
Streamlit

Used for:
- interactive dashboards
- fast Python-based UI
- real-time exploration of results

**Architecture Style**
- Medallion Architecture (Bronze / Silver / Gold)
- Hybrid Batch + Streaming system
- Incremental data processing

## Installation & Setup Instructions

### 1. Clone the repository
- git clone 
- cd Flight_Weather_Analysis
### 2. Create Python environment
- python -m venv venv  
Activate it:
Windows: venv\Scripts\activate  
Linux / Mac: source venv/bin/activate  
### 3. Install dependencies
- pip install -r requirements.txt
### 4. Start PostgreSQL
Ensure PostgreSQL service is running on your machine  
Create the database once:  
- CREATE DATABASE flights_db;  
All required tables (Bronze / Silver / Gold / Aggregations) will be automatically created by the pipeline at runtime.  
### 5. Start Kafka (Local setup)
Start Zookeeper:  
- .\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties  
Start Kafka broker:  
- .\bin\windows\kafka-server-start.bat .\config\server.properties  
### 6. Run Pipeline Components
Start orchestration server:  
- python -m orchestrator.server  
Start Kafka weather consumer (Streaming → PostgreSQL):  
- python -m ingestion.consumer_weather  
### 7. Launch Streamlit Dashboard
- streamlit run streamlit/app.py  
### 8. Start Airflow
Initialize Airflow database:  
- airflow db init  
Start scheduler:  
- airflow scheduler  
Start webserver:  
- airflow webserver  
Access Airflow UI:  
- http://localhost:8080  
