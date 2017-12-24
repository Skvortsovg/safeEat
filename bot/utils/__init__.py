# -*- coding: utf-8 -*-


from .i18n import langs
from .decorators import async, Callback, timeout, TimeoutError

from .functions import (
    send_async_message,
    send_async_location,
    send_async_photo,
    edit_async_message,
    edit_async_message_markup,
    fake_func,
    reply_typing,
    send_or_edit_message
)
from .diet import get_daily_rate