import os
import json
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
EXPERIMENTS_FILE = os.path.join(DATA_DIR, 'experiments.json')

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_experiments():
    """Retrieve all experiments."""
    _ensure_data_dir()
    if not os.path.exists(EXPERIMENTS_FILE):
        return []
    try:
        with open(EXPERIMENTS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading experiments: {e}")
        return []

def save_experiments(experiments):
    """Save the experiments list."""
    _ensure_data_dir()
    try:
        with open(EXPERIMENTS_FILE, 'w') as f:
            json.dump(experiments, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving experiments: {e}")
        return False

def add_experiment(data):
    """Add a new experiment."""
    experiments = get_experiments()
    new_exp = {
        "id": str(uuid.uuid4()),
        "name": data.get("name", "New Experiment"),
        "status": data.get("status", "planned"), # planned, active, completed, archived
        "start_date": data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
        "end_date": data.get("end_date", datetime.now().strftime("%Y-%m-%d")),
        "hypothesis": data.get("hypothesis", ""),
        "results": data.get("results", ""),
        "created_at": datetime.now().isoformat()
    }
    experiments.append(new_exp)
    save_experiments(experiments)
    return new_exp

def update_experiment(exp_id, data):
    """Update an existing experiment by ID."""
    experiments = get_experiments()
    for i, exp in enumerate(experiments):
        if exp["id"] == exp_id:
            experiments[i].update({
                "name": data.get("name", exp["name"]),
                "status": data.get("status", exp["status"]),
                "start_date": data.get("start_date", exp["start_date"]),
                "end_date": data.get("end_date", exp["end_date"]),
                "hypothesis": data.get("hypothesis", exp["hypothesis"]),
                "results": data.get("results", exp["results"]),
                "updated_at": datetime.now().isoformat()
            })
            save_experiments(experiments)
            return experiments[i]
    return None

def delete_experiment(exp_id):
    """Delete an experiment by ID."""
    experiments = get_experiments()
    new_exps = [e for e in experiments if e["id"] != exp_id]
    if len(new_exps) < len(experiments):
        save_experiments(new_exps)
        return True
    return False
