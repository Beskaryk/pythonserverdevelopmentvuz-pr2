"""Клиент HTTP API на requests."""

from http import HTTPStatus

import requests


class ApiError(Exception):
    """Ошибка HTTP API."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Client:
    """Вызовы функций слоя данных через HTTP."""

    def __init__(self, base_url="http://127.0.0.1:5000", test_client=None,
                 session=None):
        self.base_url = base_url.rstrip("/")
        self.test_client = test_client
        self.session = session or requests.Session()

    def create_participant(self, timestamp, locale, platform):
        return self._request("POST", "/core/api/participant-create", body={
            "timestamp": timestamp, "locale": locale, "platform": platform})

    def fetch_participants(self, **filters):
        return self._request("GET", "/core/api/participant-fetch",
                             query=filters)

    def inspect_participant(self, identifier):
        return self._request("GET", "/core/api/participant-inspect",
                             query={"identifier": identifier})

    def create_command(self, timestamp, content, participant, state,
                       enqueued, video=None):
        body = {
            "timestamp": timestamp, "content": content,
            "participant": participant, "state": state,
            "enqueued": enqueued}
        if video is not None:
            body["video"] = video
        return self._request("POST", "/core/api/command-create", body=body)

    def fetch_commands(self, participant, **filters):
        return self._request("GET", f"/core/api/command-fetch/{participant}",
                             query=filters)

    def inspect_command(self, identifier):
        return self._request("GET", "/core/api/command-inspect",
                             query={"identifier": identifier})

    def fetch_outputs(self, command, **filters):
        return self._request("GET", f"/core/api/output-fetch/{command}",
                             query=filters)

    def inspect_output(self, identifier):
        return self._request("GET", "/core/api/output-inspect",
                             query={"identifier": identifier})

    def fetch_report(self):
        return self._request("GET", "/core/api/report-fetch")

    def _request(self, method, path, query=None, body=None):
        headers = {"Accept": "application/json", "Accept-Language": "en"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.test_client is not None:
            response = self.test_client.open(path, method=method,
                                             headers=headers, json=body,
                                             query_string=query)
            return self._answer(response.status_code, response.get_json())
        response = self.session.request(
            method, self.base_url + path, params=query, json=body,
            headers=headers, timeout=5)
        return self._answer(response.status_code, response.json())

    @staticmethod
    def _answer(status, body):
        if status >= HTTPStatus.BAD_REQUEST:
            raise ApiError(status, body.get("error", "ошибка API"))
        return body
