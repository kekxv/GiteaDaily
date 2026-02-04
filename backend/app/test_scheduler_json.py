import json
from datetime import datetime

def test_json_serialization_with_datetime():
    # Define a simple datetime handler similar to the one in scheduler.py
    def datetime_handler(x):
        if isinstance(x, datetime):
            return x.isoformat()
        raise TypeError("Unknown type")

    # Mock data structure that caused the error
    now = datetime.now()
    raw_data_obj = {
        "activities": [
            {"created": now}
        ],
        "repo_data": {
            "owner/repo": {
                "commits": [
                    {"date": now, "sha": "1234567"}
                ]
            }
        }
    }

    # Test serialization
    try:
        json_str = json.dumps(raw_data_obj, default=datetime_handler, ensure_ascii=False)
        data = json.loads(json_str)
        
        # Verify it's correctly serialized to ISO string
        assert data["activities"][0]["created"] == now.isoformat()
        assert data["repo_data"]["owner/repo"]["commits"][0]["date"] == now.isoformat()
        print("Serialization test passed!")
    except TypeError as e:
        pytest.fail(f"Serialization failed with TypeError: {e}")

if __name__ == "__main__":
    import pytest
    test_json_serialization_with_datetime()
