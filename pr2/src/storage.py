"""Хранение данных в памяти."""

import pydantic
from pydantic import ConfigDict, TypeAdapter

SELECTION_WINDOW = 360
INT = TypeAdapter(int, config=ConfigDict(strict=True))
STR = TypeAdapter(str, config=ConfigDict(strict=True))


class StorageError(Exception):
    """Ошибка слоя данных."""


class ValidationError(StorageError):
    """Ошибка данных."""


class RecordNotFoundError(StorageError):
    """Запись не найдена."""


class MemoryStore:
    """Таблицы на словарях."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.tables = {name: {} for name in ("participant", "command",
                                             "output")}
        self.counters = {name: 0 for name in self.tables}

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
        record = self.tables["command"].get(identifier)
        if record is None:
            raise RecordNotFoundError("Command: запись не найдена")
        record["state"] = _as_str("state", state)
        return dict(record)

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
        for participant in self.tables["participant"].values():
            if participant["timestamp"] >= border:
                rows.extend(self._join(participant))
        return rows

    def close(self):
        pass

    def _insert(self, table, fields):
        self.counters[table] += 1
        record = {"identifier": self.counters[table], **fields}
        self.tables[table][record["identifier"]] = record
        return dict(record)

    def _fetch(self, table, filters):
        allowed = set(next(iter(self.tables[table].values()), {}))
        allowed.update(_fields(table))
        unknown = set(filters) - allowed
        if unknown:
            raise ValidationError(f"неизвестный фильтр: {unknown.pop()}")
        return [dict(row) for row in self.tables[table].values()
                if all(row.get(key) == value
                       for key, value in filters.items())]

    def _one(self, table, identifier):
        key = _as_int("identifier", identifier)
        if key not in self.tables[table]:
            raise RecordNotFoundError(f"{table}: запись {key} не найдена")
        return dict(self.tables[table][key])

    def _as_key(self, table, value):
        key = _as_int(table, value)
        if key not in self.tables[table]:
            raise ValidationError(f"{table}: запись {key} не найдена")
        return key

    def _join(self, participant):
        contents = [row["content"]
                    for row in self.tables["command"].values()
                    if row["participant"] == participant["identifier"]]
        return [{"content": content,
                 "locale": participant["locale"],
                 "platform": participant["platform"]}
                for content in contents or [None]]


def _fields(table):
    fields = {
        "participant": {"identifier", "timestamp", "locale", "platform"},
        "command": {"identifier", "timestamp", "content", "participant",
                    "state", "enqueued"},
        "output": {"identifier", "timestamp", "result", "state",
                   "exception", "command"},
    }
    return fields[table]


def _as_int(field, value):
    try:
        return INT.validate_python(value)
    except pydantic.ValidationError as error:
        raise ValidationError(f"{field}: ожидается int") from error


def _as_str(field, value):
    try:
        return STR.validate_python(value)
    except pydantic.ValidationError as error:
        raise ValidationError(f"{field}: ожидается str") from error
