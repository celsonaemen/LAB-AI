import json
import logging

from app.logging_config import JsonFormatter


def test_log_formatter_escapes_multiline_messages():
    record = logging.LogRecord("runtime", logging.INFO, "", 0, "started\nready", (), None)
    output = JsonFormatter().format(record)
    assert len(output.splitlines()) == 1
    assert json.loads(output)["message"] == "started\nready"
