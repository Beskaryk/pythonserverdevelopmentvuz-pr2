"""MBT для HTTP API."""

from http import HTTPStatus

import time

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule

from pr2.src.app import create_app
from pr2.src.client import ApiError, Client
from pr2.src.storage import MemoryStore

NOW = 1700000000
TEXT = st.text(alphabet=st.characters(min_codepoint=32,
                                      max_codepoint=126), max_size=8)
TIME = st.integers(min_value=NOW - 1000, max_value=NOW + 1000)
INDEX = st.integers(min_value=1, max_value=20)


class Expected:
    """Ожидаемое состояние."""

    def __init__(self):
        self.rows = {"participant": [], "command": [], "output": []}

    def add(self, table, fields):
        record = {"identifier": len(self.rows[table]) + 1, **fields}
        self.rows[table].append(record)
        return dict(record)

    def one(self, table, identifier):
        return dict(self.rows[table][identifier - 1])

    def by(self, table, field, value):
        return [dict(row) for row in self.rows[table]
                if row[field] == value]

    def report(self):
        rows = []
        for participant in self.rows["participant"]:
            if participant["timestamp"] < NOW - 360:
                continue
            commands = self.by("command", "participant",
                               participant["identifier"])
            contents = [command["content"] for command in commands] or [None]
            rows.extend({"content": content,
                         "locale": participant["locale"],
                         "platform": participant["platform"]}
                        for content in contents)
        return rows


class ApiMachine(RuleBasedStateMachine):
    """Сравнение API с эталоном."""

    participants = Bundle("participants")
    commands = Bundle("commands")

    def __init__(self):
        super().__init__()
        self.expected = Expected()
        app = create_app(testing=True, store=MemoryStore(),
                         clock=lambda: NOW)
        self.raw = app.test_client()
        self.client = Client(test_client=self.raw)

    @rule(target=participants, timestamp=TIME, locale=TEXT, platform=TEXT)
    def create_participant(self, timestamp, locale, platform):
        expected = self.expected.add("participant", {
            "timestamp": timestamp, "locale": locale, "platform": platform})
        assert self.client.create_participant(
            timestamp, locale, platform) == expected
        return expected["identifier"]

    @rule()
    def fetch_participants(self):
        assert self.client.fetch_participants() == \
            self.expected.rows["participant"]

    @rule(identifier=participants)
    def inspect_participant(self, identifier):
        assert self.client.inspect_participant(identifier) == \
            self.expected.one("participant", identifier)

    @rule(target=commands, timestamp=TIME, content=TEXT,
          participant=participants, state=TEXT, enqueued=TIME)
    def create_command(self, timestamp, content, participant, state,
                       enqueued):
        command = self.expected.add("command", {
            "timestamp": timestamp, "content": content,
            "participant": participant, "state": "done",
            "enqueued": enqueued})
        output = self.expected.add("output", {
            "timestamp": NOW, "result": "test", "state": "done",
            "exception": "", "command": command["identifier"]})
        assert self.client.create_command(
            timestamp, content, participant, state, enqueued) == {
                "command": command, "output": output}
        return command["identifier"]

    @rule(participant=participants)
    def fetch_commands(self, participant):
        assert self.client.fetch_commands(participant) == \
            self.expected.by("command", "participant", participant)

    @rule(identifier=commands)
    def inspect_command(self, identifier):
        assert self.client.inspect_command(identifier) == \
            self.expected.one("command", identifier)

    @rule(command=commands)
    def fetch_outputs(self, command):
        assert self.client.fetch_outputs(command) == \
            self.expected.by("output", "command", command)

    @rule(index=INDEX)
    def inspect_output(self, index):
        if index <= len(self.expected.rows["output"]):
            assert self.client.inspect_output(index) == \
                self.expected.one("output", index)
        else:
            with pytest.raises(ApiError) as caught:
                self.client.inspect_output(index)
            assert caught.value.status == HTTPStatus.NOT_FOUND

    @rule()
    def fetch_report(self):
        assert self.client.fetch_report() == self.expected.report()

    @rule()
    def required_headers(self):
        response = self.raw.get("/core/api/report-fetch")
        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        response = self.raw.post("/core/api/participant-create")
        assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


ApiMachine.TestCase.settings = settings(max_examples=30,
                                        stateful_step_count=25,
                                        deadline=None)
TestApi = ApiMachine.TestCase
