"""Запуск Flask-приложения."""

import argparse

from .app import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--database", default="pr2/data/audio.json")
    options = parser.parse_args()
    app = create_app(testing=options.test,
                     database_path=options.database)
    app.run(host=options.host, port=options.port)


if __name__ == "__main__":
    main()
