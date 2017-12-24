# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..')
    )
)

import re
import telegram
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)
from settings import *
import logging

logging.basicConfig(
     filename='log/bot.log',
     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
     level=logging.INFO
)

from menu import (
    BaseState as State,
    notify_developers,
    reset_user_state,
)

log = logging.getLogger(__name__)
log.debug('Starting...')


def error(bot, update, error):
    log.error('Update: %(update)r caused an error:' % vars())
    log.exception(error)
    notify_developers(bot, update, str(error))


updater = Updater(BOT_TOKEN)
updater.dispatcher.add_handler(MessageHandler(Filters.text, State))
updater.dispatcher.add_handler(CommandHandler('start', State))
updater.dispatcher.add_handler(CommandHandler('reset', reset_user_state))
updater.dispatcher.add_error_handler(error)


