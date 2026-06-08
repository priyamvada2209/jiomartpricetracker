import pytest
from unittest.mock import patch, MagicMock
import os
import requests

from jiomart_price_tracker.notifier import send_message

@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat_id"})
@patch("jiomart_price_tracker.notifier.requests.post")
def test_send_message_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    mock_post.return_value = mock_response

    send_message("Hello World")

    mock_post.assert_called_once_with(
        "https://api.telegram.org/bottest_token/sendMessage",
        json={"chat_id": "test_chat_id", "text": "Hello World"},
        timeout=30
    )

@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat_id"})
@patch("jiomart_price_tracker.notifier.requests.post")
def test_send_message_non_200_status(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_post.return_value = mock_response

    with pytest.raises(Exception, match="Telegram API returned non-200 status code: 403"):
        send_message("Hello World")

@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat_id"})
@patch("jiomart_price_tracker.notifier.requests.post")
def test_send_message_ok_false(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": False, "description": "Bad Request"}
    mock_post.return_value = mock_response

    with pytest.raises(Exception, match='Telegram returned {"ok": false}'):
        send_message("Hello World")

@patch.dict(os.environ, {}, clear=True)
def test_send_message_missing_env_vars():
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing from environment variables"):
        send_message("Hello World")
