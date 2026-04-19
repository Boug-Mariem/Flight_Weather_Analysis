from flask import Flask, jsonify
import subprocess
import sys
import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from db.postgresConnection import get_engine
import sqlalchemy as sa

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXECUTABLE = sys.executable
LOGS_DIR = PROJECT_ROOT / "logs" / "pipeline"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_ROTATION_MODE = os.getenv("PIPELINE_LOG_ROTATION_MODE", "size").strip().lower()
LOG_BACKUP_COUNT = int(os.getenv("PIPELINE_LOG_BACKUP_COUNT", "7"))
LOG_MAX_BYTES = int(os.getenv("PIPELINE_LOG_MAX_BYTES", str(2 * 1024 * 1024)))
LOG_WHEN = os.getenv("PIPELINE_LOG_WHEN", "midnight").strip().lower()
LOG_INTERVAL = int(os.getenv("PIPELINE_LOG_INTERVAL", "1"))


def _safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)


def _get_logger(section: str) -> logging.Logger:
    logger_name = f"pipeline.{section}"
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_file = LOGS_DIR / f"{_safe_name(section)}.log"
    if LOG_ROTATION_MODE == "time":
        handler = TimedRotatingFileHandler(
            log_file,
            when=LOG_WHEN,
            interval=LOG_INTERVAL,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
            utc=False,
        )
    else:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def run_module(module_name: str, section: str):
    """Run a project module, store logs by pipeline section, and return JSON status."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    logger = _get_logger(section)
    started_at = datetime.utcnow()
    logger.info("START section=%s module=%s", section, module_name)

    try:
        completed = subprocess.run(
            [PYTHON_EXECUTABLE, "-m", module_name],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        duration_seconds = (datetime.utcnow() - started_at).total_seconds()
        if completed.stdout:
            logger.info("STDOUT\n%s", completed.stdout.strip())
        if completed.stderr:
            logger.warning("STDERR\n%s", completed.stderr.strip())
        logger.info("SUCCESS section=%s module=%s duration=%.2fs", section, module_name, duration_seconds)
        return jsonify(
            {
                "status": "ok",
                "section": section,
                "module": module_name,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
                "log_file": f"logs/pipeline/{_safe_name(section)}.log",
            }
        ), 200
    except subprocess.CalledProcessError as exc:
        duration_seconds = (datetime.utcnow() - started_at).total_seconds()
        if exc.stdout:
            logger.info("STDOUT\n%s", exc.stdout.strip())
        if exc.stderr:
            logger.error("STDERR\n%s", exc.stderr.strip())
        logger.error(
            "FAILED section=%s module=%s returncode=%s duration=%.2fs",
            section,
            module_name,
            exc.returncode,
            duration_seconds,
        )
        return jsonify(
            {
                "status": "error",
                "section": section,
                "module": module_name,
                "returncode": exc.returncode,
                "stdout": (exc.stdout or "")[-4000:],
                "stderr": (exc.stderr or "")[-4000:],
                "log_file": f"logs/pipeline/{_safe_name(section)}.log",
            }
        ), 500
    except Exception as exc:
        duration_seconds = (datetime.utcnow() - started_at).total_seconds()
        logger.exception(
            "UNEXPECTED_ERROR section=%s module=%s duration=%.2fs",
            section,
            module_name,
            duration_seconds,
        )
        return jsonify(
            {
                "status": "error",
                "section": section,
                "module": module_name,
                "message": str(exc),
                "log_file": f"logs/pipeline/{_safe_name(section)}.log",
            }
        ), 500

@app.route("/ingestion")
def run_ingestion():
    return run_module("ingestion.main", "ingestion")

@app.route("/cleaning")
def run_cleaning():
    return run_module("transformation.main_clean", "cleaning")

@app.route("/gold")
def run_gold():
    return run_module("transformation.main_gold", "gold")


@app.route("/weather_analytics")
def run_Weather_analytics():
    return run_module("transformation.main_Weather_analytics", "weather_analytics")

@app.route("/airport_analytics")
def run_Airport_analytics():
    return run_module("transformation.main_Airport_analytics", "airport_analytics")

@app.route("/airline_analytics")
def run_Airline_analytics():
    return run_module("transformation.main_Airline_analytics", "airline_analytics")


@app.route("/airline_Airport_analytics")
def run_Airline_Airport_analytics():
    return run_module("transformation.main_Airline_Airport_analytics", "airline_airport_analytics")


@app.route("/prediction")
def run_Predction():
    return run_module("transformation.main_Prediction", "prediction")

@app.route("/notify_refresh")
def notify():
    logger = _get_logger("notify_dashboard")
    logger.info("START section=notify_dashboard")
    engine = get_engine()
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS pipeline_status (
        id INTEGER PRIMARY KEY,
        last_update TIMESTAMP
    );
    """
    upsert_sql = """
    INSERT INTO pipeline_status (id, last_update)
    VALUES (1, NOW())
    ON CONFLICT (id)
    DO UPDATE SET last_update = NOW();
    """
    with engine.begin() as conn:
        # 1. créer table si elle n'existe pas
        conn.execute(sa.text(create_table_sql))
        # 2. insérer ou update
        conn.execute(sa.text(upsert_sql))
    logger.info("SUCCESS section=notify_dashboard refresh signal sent")
    return jsonify(
        {
            "status": "ok",
            "section": "notify_dashboard",
            "message": "refresh signal sent",
            "log_file": "logs/pipeline/notify_dashboard.log",
        }
    ), 200


@app.route("/logs")
def list_logs():
    files = sorted(p.name for p in LOGS_DIR.glob("*.log"))
    return jsonify({"logs": files}), 200


@app.route("/logs/<section>")
def read_log(section):
    limit = 200
    log_path = LOGS_DIR / f"{_safe_name(section)}.log"
    if not log_path.exists():
        return jsonify({"status": "error", "message": "log not found"}), 404

    with log_path.open("r", encoding="utf-8", errors="replace") as file_obj:
        lines = file_obj.readlines()

    return jsonify(
        {
            "status": "ok",
            "section": section,
            "log_file": str(log_path.relative_to(PROJECT_ROOT)),
            "tail": "".join(lines[-limit:]),
        }
    ), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)