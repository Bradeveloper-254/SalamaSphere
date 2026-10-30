import getpass
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8000"


def request_json(path, method="GET", payload=None, token=None):
    headers = {"Accept": "application/json"}

    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    if token:
        headers["Authorization"] = f"Token {token}"

    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            return response.status, data

    except HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"detail": raw}

        return error.code, data


def main():
    print("SalamaSphere Day 12 integration test")
    print("Backend:", BASE_URL)

    username = input("Existing Django username: ").strip()
    password = getpass.getpass("Password: ")

    status, login_data = request_json(
        "/api/accounts/login/",
        method="POST",
        payload={
            "username": username,
            "password": password,
        },
    )

    if status != 200 or not login_data.get("token"):
        print("FAIL: Login failed.")
        print("HTTP:", status)
        print("Response:", login_data)
        return

    token = login_data["token"]
    print("PASS: Authentication succeeded.")

    device_identifier = f"DAY12-TEST-{uuid.uuid4()}"

    status, device_data = request_json(
        "/api/devices/register/",
        method="POST",
        token=token,
        payload={
            "device_name": "SalamaSphere Day 12 Test Device",
            "device_identifier": device_identifier,
            "firmware_version": "integration-test",
        },
    )

    if status not in (200, 201):
        print("FAIL: Device registration failed.")
        print("HTTP:", status)
        print("Response:", device_data)
        print(
            "Inspect the serializer requirements and retry with the "
            "fields your API requires."
        )
        return

    print("PASS: Device registration succeeded.")
    print("Device identifier:", device_identifier)
    print("Device status:", device_data.get("status"))

    if device_data.get("status") != "active":
        print("FAIL: The registered device is not active.")
        return

    client_event_id = str(uuid.uuid4())

    incident_payload = {
        "client_event_id": client_event_id,
        "device_identifier": device_identifier,
        "source": "wearable",
        "threat_level": "medium",
        "description": "Day 12 integration test incident",
    }

    status1, incident1 = request_json(
        "/api/incidents/",
        method="POST",
        token=token,
        payload=incident_payload,
    )

    if status1 not in (200, 201) or not incident1.get("id"):
        print("FAIL: Initial incident creation failed.")
        print("HTTP:", status1)
        print("Response:", incident1)
        return

    incident_id_1 = str(incident1["id"])
    print("PASS: Initial incident created.")
    print("Server incident ID:", incident_id_1)

    status2, incident2 = request_json(
        "/api/incidents/",
        method="POST",
        token=token,
        payload=incident_payload,
    )

    if status2 not in (200, 201) or not incident2.get("id"):
        print("FAIL: Retry failed.")
        print("HTTP:", status2)
        print("Response:", incident2)
        return

    incident_id_2 = str(incident2["id"])

    if incident_id_1 != incident_id_2:
        print("FAIL: Retry created or returned a different incident.")
        print("First ID:", incident_id_1)
        print("Retry ID:", incident_id_2)
        return

    print("PASS: Retry returned the same server incident ID.")
    print("PASS: Server-side duplicate protection behaved as expected.")
    print()
    print("RESULT: Django authentication and metadata idempotency passed.")
    print(
        "NOTE: Flutter SQLite acknowledgment and evidence-file uploads "
        "must be verified separately."
    )


if __name__ == "__main__":
    try:
        main()
    except URLError as error:
        print("FAIL: Could not connect to Django.")
        print(error)