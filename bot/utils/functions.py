# -*- coding: utf-8 -*-


from .decorators import async
import time
import logging

log = logging.getLogger(__name__)
import telegram
from telegram.error import BadRequest
from .decorators import timeout

MAX_RETRIES = 5
WAIT_TIME = 0.5


@async
def send_async_message(bot, update, text, markup=None, parse_mode=None, disable_web_page_preview=True, disable_notification=False, pipe=None):
    if update.message is None:
        log.error('function send_async_message: `update.message` is None')
        return

    retries_left = MAX_RETRIES

    chat_id = update.message.chat_id

    log.info('Sending message to %(chat_id)d' % dict(chat_id=chat_id))

    while retries_left > 0:

        try:
            msg = bot.sendMessage(
                chat_id=chat_id,
                text=text,
                reply_markup=markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
            )
        except Exception as err:
            log.exception(err)
            retries_left -= 1
            if retries_left < 1:
                log.critical('Failed to send message to %(chat_id)d' % dict(chat_id=chat_id))
                if pipe is not None:
                    pipe.send('123456')
                return

            log.warning(
                'Failed attempt to send message [%(cn)d/%(tn)d] '
                'to %(chat_id)d. Will try again via '
                '%(num).2f seconds' % dict(
                    chat_id=chat_id,
                    num=WAIT_TIME,
                    tn=MAX_RETRIES,
                    cn=retries_left,
                )
            )
            time.sleep(WAIT_TIME)
        else:
            if pipe is not None:
                pipe.send(msg)
            return


@async
def send_async_photo(bot, update, img, parse_mode=None, disable_web_page_preview=True, disable_notification=False):
    if update.message is None:
        log.error('function send_async_photo: `update.message` is None')
        return

    retries_left = MAX_RETRIES

    chat_id = update.message.chat_id

    log.info('Sending photo to %(chat_id)d' % dict(chat_id=chat_id))

    while retries_left > 0:

        try:
            resp = bot.sendPhoto(
                chat_id=chat_id,
                photo=img,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
            )

            # try:
            #     for obj in resp.photo:
            #         log.info(u'bot.sendPhoto response: %r', obj.file_id)
            # except Exception as err:
            #     log.exception(err)
        except Exception as err:
            log.exception(err)
            retries_left -= 1
            if retries_left < 1:
                log.critical('Failed to send photo to %(chat_id)d' % dict(chat_id=chat_id))
                break

            log.warning(
                'Failed attempt to send photo [%(cn)d/%(tn)d] '
                'to %(chat_id)d. Will try again via '
                '%(num).2f seconds' % dict(
                    chat_id=chat_id,
                    num=WAIT_TIME,
                    tn=MAX_RETRIES,
                    cn=retries_left,
                )
            )
            time.sleep(WAIT_TIME)

        else:
            break

    if issubclass(type(img), file):
        img.close()


@async
def send_async_location(bot, update, latitude=0.0, longitude=0.0, markup=None, disable_notification=False):

    if update.message is None:
        log.error('function send_async_location: `update.message` is None')
        return

    retries_left = MAX_RETRIES

    chat_id = update.message.chat_id

    log.info('Sending message to %(chat_id)d' % dict(chat_id=chat_id))

    while retries_left > 0:

        try:
            bot.sendLocation(
                chat_id=chat_id,
                latitude=latitude,
                longitude=longitude,
                reply_markup=markup,
                disable_notification=disable_notification,
            )

        except Exception as err:
            log.exception(err)
            retries_left -= 1
            if retries_left < 1:
                log.critical('Failed to send message to %(chat_id)d' % dict(chat_id=chat_id))
                return

            log.warning(
                'Failed attempt to send message [%(cn)d/%(tn)d] '
                'to %(chat_id)d. Will try again via '
                '%(num).2f seconds' % dict(
                    chat_id=chat_id,
                    num=WAIT_TIME,
                    tn=MAX_RETRIES,
                    cn=retries_left,
                )
            )
            time.sleep(WAIT_TIME)

        else:
            return

from .exceptions import FailedToSendMessage

@async
def edit_async_message(bot, update, text, img=None,  markup=None, parse_mode=None, disable_web_page_preview=True, pipe=None):
    query = update.callback_query

    if query.message is None:
        log.error('function edit_async_message: `query.message` is None')
        return

    retries_left = MAX_RETRIES

    chat_id = query.message.chat_id
    message_id = query.message.message_id

    log.info('Sending message edit to %(chat_id)d:%(message_id)d' % dict(
        chat_id=chat_id,
        message_id=message_id,
    ))

    while retries_left > 0:

        try:
            msg = bot.editMessageText(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        except Exception as err:
            log.exception(err)
            retries_left -= 1
            if retries_left < 1:
                log.critical('Failed to send message to %(chat_id)d' % dict(chat_id=chat_id))
                if pipe is not None:
                    pipe.send('123456')
                return

            log.warning(
                'Failed attempt to send message [%(cn)d/%(tn)d] '
                'to %(chat_id)d. Will try again via '
                '%(num).2f seconds' % dict(
                    chat_id=chat_id,
                    num=WAIT_TIME,
                    tn=MAX_RETRIES,
                    cn=retries_left,
                )
            )
            time.sleep(WAIT_TIME)

        else:
            if pipe is not None:
                    pipe.send(msg)
            return

@async
def edit_async_message_markup(bot, update, markup=None):

    query = update.callback_query

    if query.message is None:
        log.error('function edit_async_markup: `query.message` is None')
        return

    retries_left = MAX_RETRIES

    chat_id = query.message.chat_id
    message_id = query.message.message_id

    log.info('Sending message to %(chat_id)d:%(message_id)d' % dict(
        chat_id=chat_id,
        message_id=message_id,
    ))

    while retries_left > 0:

        try:
            bot.editMessageReplyMarkup(
                chat_id=chat_id,
                message_id=query.message.message_id,
                reply_markup=markup,
            )

        except Exception as err:
            log.exception(err)
            retries_left -= 1
            if retries_left < 1:
                log.critical('Failed to send message to %(chat_id)d' % dict(chat_id=chat_id))
                return

            log.warning(
                'Failed attempt to send message [%(cn)d/%(tn)d] '
                'to %(chat_id)d. Will try again via '
                '%(num).2f seconds' % dict(
                    chat_id=chat_id,
                    num=WAIT_TIME,
                    tn=MAX_RETRIES,
                    cn=retries_left,
                )
            )
            time.sleep(WAIT_TIME)

        else:
            return

@async
def fake_func(*args):
    pass

@async
def reply_typing(bot, update):
    try:
        chat_id = update.message.chat_id
    except AttributeError:
        chat_id = update.callback_query.message.chat.id
    log.info('Sending typing action to %(chat_id)d' % dict(chat_id=chat_id))
    bot.sendChataction(chat_id=chat_id,
                       action=telegram.ChatAction.TYPING)

@async
def send_or_edit_message(bot, update, text=None, markup=None, parse_mode=None, disable_web_page_preview=True, pipe=None):
    kwargs = dict(
        reply_markup=markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )

    # if text:
    kwargs['text'] = text

    query = getattr(update, 'callback_query', None)

    if query:
        kwargs['chat_id'] = query.message.chat_id
        kwargs['message_id'] = query.message.message_id
        func = getattr(bot, 'editMessageText')
    else:
        kwargs['chat_id'] = update.message.chat_id
        func = getattr(bot, 'sendMessage')
    log.info('kwargs={}'.format(kwargs))

    msg = func(**kwargs)
    if pipe is not None:
        pipe.send(msg)
    log.info('~_~_~_~_~_~_~_~__~_~_~_~_~_~__~~__~_~_~__~_~_~_~_')
    # log.error('**************************************************************')
    # log.info(parse_mode)
    # query = getattr(update, 'callback_query', None)
    # if query:
    #     edit_async_message(bot, update, text, markup, parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=disable_web_page_preview)
    #
    # else:
    #     send_async_message(bot, update, text, markup, parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=disable_web_page_preview)
