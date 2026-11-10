"""HTTP API на Flask."""

import time
from base64 import b64decode
from binascii import Error as DecodeError
from http import HTTPStatus
from pathlib import Path
from threading import Lock

import pydantic
from flask import (Blueprint, Flask, current_app, g, jsonify,
                   render_template, request, send_from_directory)
from pydantic import BaseModel
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from .executor import JobQueue, complete, create_command
from .schemas import (CommandCreate, CommandFilters, IdentifierQuery,
                      OutputFilters, ParticipantCreate, ParticipantFilters)
from .storage import MemoryStore, RecordNotFoundError, ValidationError


api = Blueprint("api", __name__)
VIDEO_LIMIT = 10 * 1024 * 1024
REQUEST_LIMIT = 14 * 1024 * 1024


def create_app(testing=False, store=None, clock=time.time):
    app = Flask(__name__, template_folder="../templates")
    app.config.update(TESTING=testing, MAX_CONTENT_LENGTH=REQUEST_LIMIT,
                      STORE=store or MemoryStore(),
                      CLOCK=clock,
                      RESULT_DIR=Path(__file__).parents[1] / "data/audio")

    lock = Lock()
    app.config["STORE_LOCK"] = lock
    if not testing:
        app.config["JOBS"] = JobQueue(app.config["STORE"],
                                      app.config["RESULT_DIR"], clock, lock)
    app.before_request(prepare_request)
    app.teardown_request(release_store)
    app.register_blueprint(api)
    return app


def prepare_request():
    if request.endpoint in {"api.index", "api.download_audio"}:
        return None
    response = check_headers()
    if response is not None:
        return response
    lock = current_app.config["STORE_LOCK"]
    lock.acquire()
    g.store_lock = lock
    return None


def release_store(exception):
    lock = g.pop("store_lock", None)
    if lock is not None:
        lock.release()


@api.get("/")
def index():
    return render_template("index.html")


@api.get("/audio/<uuid:identifier>")
def download_audio(identifier):
    return send_from_directory(
        current_app.config["RESULT_DIR"], f"{identifier}.mp3",
        as_attachment=True, download_name="audio.mp3")


@api.app_errorhandler(RequestEntityTooLarge)
def large_request(exception):
    return error("Файл слишком большой", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)


def check_headers():
    if request.method in {"POST", "PUT", "PATCH"} \
            and request.mimetype != "application/json":
        return error("Content-Type должен быть application/json", 415)
    if request.headers.get("Accept") != "application/json":
        return error("Accept должен быть application/json", 406)
    if request.headers.get("Accept-Language") != "en":
        return error("Accept-Language должен быть en", 406)
    return None


@api.app_errorhandler(RecordNotFoundError)
def not_found(exception):
    return error(str(exception), 404)


@api.app_errorhandler(ValidationError)
@api.app_errorhandler(BadRequest)
def invalid(exception):
    return error(str(exception), 400)


@api.app_errorhandler(pydantic.ValidationError)
def schema_invalid(exception):
    return error("неверные входные данные", 400)


@api.post("/core/api/participant-create")
def participant_create():
    body = json_body(ParticipantCreate)
    return jsonify(data_store().create_participant(
        body.timestamp, body.locale, body.platform))


@api.get("/core/api/participant-fetch")
def participant_fetch():
    filters = query_values(ParticipantFilters)
    return jsonify(data_store().fetch_participants(**filters))


@api.get("/core/api/participant-inspect")
def participant_inspect():
    identifier = required_identifier()
    return jsonify(data_store().inspect_participant(identifier))


@api.post("/core/api/command-create")
def command_create():
    body = json_body(CommandCreate)
    if current_app.config["TESTING"]:
        command = create_command(data_store(), body, "queued")
        return jsonify(complete(data_store(), current_app.config["CLOCK"],
                                command["identifier"], "test", "done", ""))
    video = decode_video(body)
    command = current_app.config["JOBS"].submit(body, video)
    if command is None:
        return error("Очередь заполнена", HTTPStatus.SERVICE_UNAVAILABLE)
    return jsonify({"command": command, "output": None})


def decode_video(body):
    if not body.video or not body.content.lower().endswith(".mp4"):
        raise ValidationError("Нужен MP4-файл в поле video")
    try:
        video = b64decode(body.video, validate=True)
    except (DecodeError, ValueError) as exception:
        raise ValidationError("Некорректный Base64") from exception
    if len(video) > VIDEO_LIMIT:
        raise RequestEntityTooLarge()
    return video


@api.get("/core/api/command-fetch/<int:participant>")
def command_fetch(participant):
    filters = query_values(CommandFilters)
    return jsonify(data_store().fetch_commands(participant, **filters))


@api.get("/core/api/command-inspect")
def command_inspect():
    return jsonify(data_store().inspect_command(required_identifier()))


@api.get("/core/api/output-fetch/<int:command>")
def output_fetch(command):
    filters = query_values(OutputFilters)
    return jsonify(data_store().fetch_outputs(command, **filters))


@api.get("/core/api/output-inspect")
def output_inspect():
    return jsonify(data_store().inspect_output(required_identifier()))


@api.get("/core/api/report-fetch")
def report_fetch():
    moment = int(current_app.config["CLOCK"]())
    return jsonify(data_store().fetch_report(moment))


def data_store():
    return current_app.config["STORE"]


def json_body(model):
    return model.model_validate(request.get_json())


def query_values(model: type[BaseModel]):
    values = model.model_validate(request.args.to_dict())
    return values.model_dump(exclude_none=True)


def required_identifier():
    values = IdentifierQuery.model_validate(request.args.to_dict())
    return values.identifier


def error(message, status):
    return jsonify({"error": message}), status
