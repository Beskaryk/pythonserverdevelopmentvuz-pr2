"""Хранение данных в TinyDB."""

from pathlib import Path

from tinydb import Query, TinyDB

from .storage import (RecordNotFoundError, SELECTION_WINDOW,
                      ValidationError, _as_int, _as_str, _fields)


class TinyStore:
    """Таблицы в JSON-файле TinyDB."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database = TinyDB(path)

    def reset(self):
        self.database.drop_tables()

    def close(self):
        self.database.close()

    def fail_interrupted(self, moment):
        query = Query().state.one_of(["queued", "running"])
        for command in self._table("command").search(query):
            identifier = command["identifier"]
            if not self.fetch_outputs(identifier):
                self.create_output(moment, "", "failed",
                                   "Сервер был перезапущен", identifier)
            output = self.fetch_outputs(identifier)[0]
            self.update_command_state(identifier, output["state"])

    def create_participant(self, timestamp, locale, platform):
        return self._insert("participant", {
            "timestamp": _as_int("timestamp", timestamp),
            "locale": _as_str("locale", locale),
            "platform": _as_str("platform", platform),
        })

    def fetch_participants(self, **filters):
        return self._fetch("participant", filters)

    def inspect_participant(self, identifier):
        return self._one("participant", identifier)

    def create_command(self, timestamp, content, participant, state,
                       enqueued):
        return self._insert("command", {
            "timestamp": _as_int("timestamp", timestamp),
            "content": _as_str("content", content),
            "participant": self._as_key("participant", participant),
            "state": _as_str("state", state),
            "enqueued": _as_int("enqueued", enqueued),
        })

    def fetch_commands(self, participant, **filters):
        filters["participant"] = _as_int("participant", participant)
        return self._fetch("command", filters)

    def inspect_command(self, identifier):
        return self._one("command", identifier)

    def update_command_state(self, identifier, state):
        key = _as_int("identifier", identifier)
        record = self._table("command").get(Query().identifier == key)
        if record is None:
            raise RecordNotFoundError("Command: запись не найдена")
        self._table("command").update(
            {"state": _as_str("state", state)}, Query().identifier == key)
        return self._one("command", key)

    def create_output(self, timestamp, result, state, exception, command):
        return self._insert("output", {
            "timestamp": _as_int("timestamp", timestamp),
            "result": _as_str("result", result),
            "state": _as_str("state", state),
            "exception": _as_str("exception", exception),
            "command": self._as_key("command", command),
        })

    def fetch_outputs(self, command, **filters):
        filters["command"] = _as_int("command", command)
        return self._fetch("output", filters)

    def inspect_output(self, identifier):
        return self._one("output", identifier)

    def fetch_report(self, moment):
        border = _as_int("moment", moment) - SELECTION_WINDOW
        rows = []
        for participant in self._table("participant").all():
            if participant["timestamp"] >= border:
                rows.extend(self._join(participant))
        return rows

    def _insert(self, table, fields):
        rows = self._table(table).all()
        identifier = max((row["identifier"] for row in rows), default=0) + 1
        record = {"identifier": identifier, **fields}
        self._table(table).insert(record)
        return dict(record)

    def _fetch(self, table, filters):
        unknown = set(filters) - _fields(table)
        if unknown:
            raise ValidationError(f"неизвестный фильтр: {unknown.pop()}")
        return [dict(row) for row in self._table(table).all()
                if all(row.get(key) == value
                       for key, value in filters.items())]

    def _one(self, table, identifier):
        key = _as_int("identifier", identifier)
        record = self._table(table).get(Query().identifier == key)
        if record is None:
            raise RecordNotFoundError(f"{table}: запись {key} не найдена")
        return dict(record)

    def _as_key(self, table, value):
        key = _as_int(table, value)
        if self._table(table).get(Query().identifier == key) is None:
            raise ValidationError(f"{table}: запись {key} не найдена")
        return key

    def _join(self, participant):
        contents = [row["content"] for row in self._table("command").all()
                    if row["participant"] == participant["identifier"]]
        return [{"content": content,
                 "locale": participant["locale"],
                 "platform": participant["platform"]}
                for content in contents or [None]]

    def _table(self, name):
        return self.database.table(name)
