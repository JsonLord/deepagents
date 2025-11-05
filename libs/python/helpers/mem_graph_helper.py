import requests
import json
import uuid

from python.helpers.log import Log
import re

log = Log()

class MemGraphHelper:
    _instance = None

    @staticmethod
    def get_instance():
        if MemGraphHelper._instance is None:
            MemGraphHelper._instance = MemGraphHelper()
        return MemGraphHelper._instance

    def __init__(self, base_url="https://harvesthealth-mem-graph.hf.space/mcp"):
        if MemGraphHelper._instance is not None:
            raise Exception("This class is a singleton!")
        self.api_url = base_url
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}
        self.csrf_token = self._get_csrf_token()

    def disconnect(self):
        self.session.close()
        MemGraphHelper._instance = None

    def _get_csrf_token(self):
        try:
            response = self.session.get(self.api_url)
            response.raise_for_status()
            match = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', response.text)
            if match:
                return match.group(1)
            return None
        except requests.exceptions.RequestException as e:
            log.log("error", f"API Request Error: {e}")
            return None

    def _send_command(self, command: str) -> dict:
        payload = {"command": command, "csrf_token": self.csrf_token}
        try:
            response = self.session.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.log("error", f"API Request Error: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            log.log("error", f"JSON Decode Error: {e.msg} at line {e.lineno} column {e.colno}", f"Response text: {response.text}")
            return {"error": "JSON Decode Error"}

    def load_history(self, conversation_id: str) -> list:
        key = f"chat_history:{conversation_id}"
        log.log("info", f"<- Loading history for key: {key}")
        response_data = self._send_command(f"GET {key}")
        log.log("info", f"Load response: {response_data}")

        if "response" in response_data and response_data["response"] != "(nil)":
            try:
                response_str = response_data["response"]
                if response_str.startswith("'") and response_str.endswith("'"):
                    response_str = response_str[1:-1]
                return json.loads(response_str)
            except json.JSONDecodeError as e:
                log.log("error", f"Error: Could not decode JSON from response: {e}")
                return []
        return []

    def save_history(self, conversation_id: str, history: list):
        key = f"chat_history:{conversation_id}"
        value = f"'{json.dumps(history)}'"
        log.log("info", f"-> Saving history for key: {key}")
        response_data = self._send_command(f"SET {key} {value}")
        log.log("info", f"Save response: {response_data}")

        if "response" in response_data and "OK" in response_data["response"]:
            log.log("info", " Save successful.")
        else:
            log.log("error", f" Save failed. Response: {response_data}")
