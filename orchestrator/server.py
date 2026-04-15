from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/ingestion")
def run_ingestion():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "ingestion.main"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    return "ingestion done", 200

@app.route("/cleaning")
def run_cleaning():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_clean"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    return "cleaning done", 200

@app.route("/gold")
def run_gold():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_gold"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    
    return "gold done", 200


@app.route("/weather_analytics")
def run_Weather_analytics():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_Weather_analytics"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    return "Weather_analytics done", 200

@app.route("/airport_analytics")
def run_Airport_analytics():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_Airport_analytics"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    
    return "Airport_analytics done", 200

@app.route("/airline_analytics")
def run_Airline_analytics():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_Airline_analytics"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )

    return "Airline_analytics done", 200


@app.route("/airline_Airport_analytics")
def run_Airline_Airport_analytics():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_Airline_Airport_analytics"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    return "Airline_Airport_analytics done", 200


@app.route("/prediction")
def run_Predction():
    subprocess.run(
        [
            r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis\flightsWeather39\Scripts\python.exe",
            "-m",
            "transformation.main_Prediction"
        ],
        cwd=r"D:\Programmation_ING2\S2\Data_engineering\Projet\Flight_Weather_Analysis"
    )
    return "Prediction done", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)