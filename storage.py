import json
import os

USAGE_FILE = "usage_log.json"


def load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_user_paid(user_id):
    data = load_usage()
    return data.get(user_id, {}).get("is_paid", False)


def mark_user_paid(user_id):
    data = load_usage()

    if user_id not in data:
        data[user_id] = {
            "count": 0,
            "total_runs": 0,
            "last_used": None,
            "is_paid": False
        }

    data[user_id]["is_paid"] = True
    save_usage(data)
