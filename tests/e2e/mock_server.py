# tests/e2e/mock_server.py
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# A simple in-memory store for received requests
received_requests = {
    "slack": [],
    "jira": [],
    "sms": []
}

@app.route('/slack', methods=['POST'])
def mock_slack():
    data = request.json
    print(f"Mock Slack received: {data}")
    received_requests["slack"].append(data)
    return "ok"

@app.route('/jira/rest/api/2/issue', methods=['POST'])
def mock_jira_create():
    data = request.json
    print(f"Mock Jira (create issue) received: {data}")
    issue_key = f"TEST-{len(received_requests['jira']) + 1}"
    received_requests["jira"].append({"type": "create", "data": data, "key": issue_key})
    return jsonify({"key": issue_key}), 201

@app.route('/sms/send', methods=['POST'])
def mock_sms_provider():
    data = request.json
    print(f"Mock SMS Provider received: {data}")
    received_requests["sms"].append({
        "recipients": data.get("recipients"),
        "message": data.get("messages")[0] if data.get("messages") else None
    })
    return jsonify({
        "messages": [
            {"status": 0, "recipient": r} for r in data.get("recipients", [])
        ]
    }), 200

@app.route('/check', methods=['GET'])
def check_requests():
    return jsonify(received_requests)

@app.route('/clear', methods=['POST'])
def clear_requests():
    global received_requests
    received_requests = {"slack": [], "jira": [], "sms": []}
    print("--- Mock Server data cleared ---")
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)