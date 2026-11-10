# Практическая работа №2. Вариант 5

Тема курсовой: веб-приложение с HTTP API для асинхронного извлечения
звука в формате MP3 из файлов MP4.

В Windows из корня репозитория запусти `.\run.bat`. Скрипт создаёт
`.venv`, устанавливает зависимости и запускает текущий этап.
В терминале VS Code используется та же команда.

## Этап 1. Конвертер MP4 в MP3

`pr2/src/converter.py` читает байты MP4 из стандартного ввода.
FFmpeg извлекает первую аудиодорожку и сохраняет её как MP3.
Параметр `--output` задаёт путь к результату. Пример для cmd:

```bat
.venv\Scripts\python.exe -m pr2.src.converter --output audio.mp3 < video.mp4
```

`pr2/src/demo.py` создаёт три коротких видео с разными звуковыми
частотами и получает три MP3 в `pr2/data/examples`.

## Этап 2. Flask API

После запуска открой [страницу приложения](http://127.0.0.1:5000/).
Выбери MP4 до 10 МиБ и нажми **Извлечь звук**. Страница отправит задачу,
покажет её состояние и предложит скачать MP3.

- `server.py` запускает Flask. Параметры `--host` и `--port` задают адрес.
- `app.py` содержит маршруты и проверку заголовков, `schemas.py` проверяет данные.
- `executor.py` ставит задачи в очередь и запускает утилиту через subprocess.
- `storage.py` хранит участников, команды и результаты в памяти.
- `client.py` содержит Python-клиент, `test_api_mbt.py` — модель Hypothesis.

### Маршруты

Префикс маршрутов из таблицы — `/core/api/`.
Заголовки `Accept: application/json` и `Accept-Language: en` обязательны.
Для POST требуется также `Content-Type: application/json`.

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| POST | participant-create | Создаёт участника по `timestamp`, `locale`, `platform`. |
| GET | participant-fetch | Список участников с необязательными фильтрами. |
| GET | participant-inspect | Участник по `?identifier=…`. |
| POST | command-create | Принимает задачу и сразу возвращает её в состоянии `queued`. |
| GET | command-fetch/:participant | Список команд участника. |
| GET | command-inspect | Команда и её состояние по `?identifier=…`. |
| GET | output-fetch/:command | Результаты команды. До завершения возвращает пустой список. |
| GET | output-inspect | Результат по `?identifier=…`. |
| GET | report-fetch | Имена файлов, локали и платформы участников за последние шесть минут. |

В теле `command-create` передаются `timestamp`, имя файла `content`,
ID участника `participant`, `state`, время постановки `enqueued` и
`video` (байты MP4 в Base64). Сервер сам выставляет состояния
`queued`, `running` и `done` или `failed`. После завершения в
`Output.result` появляется ссылка для скачивания `/audio/<uuid>`.
Ошибка преобразования записывается в `Output.exception`.

`.\run.bat --test` запускает сервер с фиксированным результатом `test`.
В этом режиме для команды можно опустить `video`.

Запуск тестов и отчёта о покрытии ветвей:

```powershell
.\.venv\Scripts\python.exe -m coverage run --branch --source=pr2/src -m pytest pr2/tests -q
.\.venv\Scripts\python.exe -m coverage report -m
```

## Этап 3. TinyDB

`tiny_storage.py` сохраняет участников, команды и результаты в
`pr2/data/audio.json`. Другой файл можно выбрать через `--database`.
Готовый MP3 хранится в `pr2/data/audio`. После перезапуска с тем же
файлом базы результаты доступны по прежним ссылкам. Прерванные задачи
помечаются как `failed`, видео нужно отправить повторно.

Модельные тесты используют отдельную временную базу.
