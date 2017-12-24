# -*- coding: utf-8 -*-

try:
    import cPickle as pickle
except (ImportError, ModuleNotFoundError):
    import pickle

import logging
import re
import threading
import os
from math import sqrt, floor
import weakref
from functools import wraps
from multiprocessing import Pipe

import telegram
import settings
from cache import Context
from utils import (
    langs,
    send_async_message,
    get_daily_rate,
)
from db_interface import (
    reg_user,
    set_usernorm,
    get_daily_report,
    get_daily_norm,
    add_new_dish,
    get_ingredients_types,
    get_inrgediets_by_type,
    add_di,
    is_dish_exist,
    calc_dish_features,
    get_curr_user_features,
    update_users_features,
    delete_user,
)
import string
import random
import base64
from datetime import datetime

s = string.ascii_lowercase + string.digits

log = logging.getLogger(__name__)


class CallbackEncoder:

    def __init__(self):
        self._cb = []
        # self._callback_module = weakref.ref(callback_module)

    def encode(self, func, args, kwargs):
        func_name = func.__name__
        if not func_name in self._cb:
            self._cb.append(func_name)
        func_id = self._cb.index(func_name)
        dump = pickle.dumps((func_id, args, kwargs), pickle.HIGHEST_PROTOCOL)
        return base64_encode(dump)

    def decode(self, message):
        msg = base64_decode(message)
        func_id, args, kwargs = pickle.loads(msg)
        if func_id >= len(self._cb):
            return
        func_name = self._cb[func_id]
        func = globals().get(func_name, None)
        # func = getattr(callback_module, func_name, None)
        return func, args, kwargs


def to_bytes(s, encoding='utf-8', errors='ignore'):
    if isinstance(s, str):
        return s.encode(encoding, errors)
    elif isinstance(s, bytearray):
        return str(s)
    return s



def base64_encode(s):
    """ base64 encodes a single bytestring (and is tolerant to getting
    called with a unicode string). The resulting bytestring is safe
    for putting into URLs """
    # s = to_bytes(s)
    return base64.urlsafe_b64encode(s).rstrip(b'=').decode('utf-8', 'ignore')


def base64_decode(s):
    """ base64 decodes a single bytestring (and is tolerant to getting
    called with a unicode string). The result is also a bytestring """
    # s = to_bytes(s, encoding='ascii', errors='ignore')
    ls = len(s)
    n = -ls % 4
    s = s.ljust(ls + n, '=')
    try:
        return base64.urlsafe_b64decode(s)
    except (TypeError, ValueError):
        raise ValueError('Invalid base64-encoded data')


cbe = CallbackEncoder()


class InlineKeyboard(object):

    def __init__(self, cbe):
        self.keyboard = []
        self.row = []
        self.cbe = cbe

    def add_button(self, name, callback=None, *args, **kwargs):
        if not callable(callback):
            callback = ignore_callback
        cb = self.cbe.encode(callback, args, kwargs)
        self.row.append(telegram.InlineKeyboardButton(name, callback_data=cb))

    def next_line(self):
        self.keyboard.append(self.row)
        self.row = []

    def __call__(self):
        if len(self.row) > 0:
            self.next_line()
        return self.keyboard



class BaseState(object):
    """ Initial session state """

    # Parent class for "back" and "cancel" buttons
    parent = None
    # Is user need to authorized to enter the state
    auth_required = False

    def __init__(self, bot, update):

        self.bot = weakref.proxy(bot)
        self.update = weakref.proxy(update)
        self.ctx = Context(update.message.chat_id)

        ctx = self.ctx

        ctx.p_get_state()
        ctx.p_get_lang()
        ctx.p_get_authorized()
        ctx.p_incr_requests_n()
        state, lang, is_authorized, z = ctx.apply()

        log.info(
            (
                'chat:{chat} user:{u.name} id:{u.id} '
                'state is {state}.'
            ).format(
                u=update.message.from_user,
                chat=update.message.chat_id,
                state=str(state),
            )
        )

        if lang is None:
            lang = settings.DEFAULT_LANGUAGE
            ctx.p_set_lang(lang)

        ctx.apply()
        langs[lang].install()

        if not state:
            log.info(
                (
                    'chat:{chat} user:{u.name} id:{u.id} '
                    'state is {state}. Going to UnAuthorizedState'
                ).format(
                    u=update.message.from_user,
                    chat=update.message.chat_id,
                    state=state,
                )
            )
            self.new_state(UnAuthorizedState)
        else:
            klass = globals().get(state, UnAuthorizedState.__name__)

            if klass.auth_required is True and not is_authorized:
                warn_msg = (
                    'chat:{chat} user:{u.name} id:{u.id} '
                    'WARNING: probably logic error. '
                    'Tried to enter authorized state '
                    'from unauthorized menu level'
                ).format(
                    u=update.message.from_user,
                    chat=update.message.chat_id,
                )
                log.warning(warn_msg)
                state = None

            self.__class__ = klass
            # value = update.message.text.encode('utf-8') # Python 2
            value = update.message.text # Python 3
            # if value == '/start':
            #     self.on_enter(text=_('GREET_USER_TEXT'))
            # else:
            self.on_input(value)

    def on_enter(self, **kwargs):
        """ This method is called when ctx enters new state """

    def on_input(self, value):
        """ This method is called on ctx input """

    def __str__(self):
        return self.__class__.__name__

    def save_state(self, timeout=None):
        """ Save current ctx to storage """
        name = str(self)

        log.info(
            (
                'chat:{chat} user:{u.name} id:{u.id} '
                'saving session state:{name} timeout:{tmout}'
            ).format(
                u=self.update.message.from_user,
                chat=self.update.message.chat_id,
                name=name,
                tmout=timeout,
            )
        )

        self.ctx.p_set_state(str(self), timeout=timeout)
        self.ctx.apply()

    def new_state(self, state, **kwargs):
        """ Enter another state """
        parent = str(self)

        log.info(
            (
                'chat:{chat} user:{u.name} id:{u.id} '
                'enter new state:{state} from:{parent}'
            ).format(
                u=self.update.message.from_user,
                chat=self.update.message.chat_id,
                state=state,
                parent=parent,
            )
        )

        ctx = self.ctx
        ctx.p_get_authorized()
        ctx.p_incr_requests_n()
        is_authorized, z = ctx.apply()

        if state is not None:
            self.__class__ = state
            # self.parent = parent

            if self.auth_required is True and not is_authorized:
                warn_msg = (
                    'chat:{chat} user:{u.name} id:{u.id} '
                    'WARNING: probably logic error. '
                    'Tried to enter authorized state '
                    'from unauthorized menu level'
                ).format(
                    u=self.update.message.from_user,
                    chat=self.update.message.chat_id,
                )
                log.warning(warn_msg)
                ctx.set_state(None)
                self.new_state(UnAuthorizedState)

            tmout = settings.SESSION_TIMEOUT if is_authorized is True else None
            self.save_state(timeout=tmout)
            self.on_enter(**kwargs) # self._on_enter(**kwargs) # <===== HERE
        else:
            warn_msg = (
                'chat:{chat} user:{u.name} id:{u.id} '
                'WARNING! State can not be "None" (probably logic error). '
                'Doing nothing'
            ).format(
                u=self.update.message.from_user,
                chat=self.update.message.chat_id,
            )
            log.warning(warn_msg)


#@async
def notify_developers(bot, update, text):
    if 'DEVELOPERS_CHAT_ID' in vars(settings):
        send_async_message(
            bot,
            update,
            text,
        )
        #bot.sendMessage(
        #    settings.DEVELOPERS_CHAT_ID,
        #    text=text,
        #)


def back_button(func):
    @wraps(func)
    def wrapper(self, value):
        if value in (_('LABEL_BACK_BUTTON'), _('LABEL_CANCEL_BUTTON')):
            log.info(
                (
                    'chat:{chat} user:{u.name} id:{u.id} '
                    'user clicked "back" or "cancel" button'
                ).format(
                    u=self.update.message.from_user,
                    chat=self.update.message.chat_id,
                )
            )
            self.new_state(self.parent, text='Ok')
        else:
            return func(self, value)
    return wrapper

def get_thread(ident):
    if ident is None:
        return
    idents = [i.ident for i in threading.enumerate()]
    if ident in idents:
        i = idents.index(ident)
        return threading.enumerate()[i]


class UnAuthorizedState(BaseState):
    parent = None

    def on_enter(self, text=None):
        if text is None:
            text = _('UNAUTHORIZED_STATE_TEXT')

        markup = telegram.ReplyKeyboardMarkup(
            [[
            ], [
                telegram.KeyboardButton(_('LABEL_REGISTER_BUTTON')),
            ]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        send_async_message(self.bot, self.update, text, markup=markup)

    def on_input(self, value):
        if value == _('LABEL_REGISTER_BUTTON'):
            self.new_state(RegisteringNameState)


class RegisteringNameState(BaseState):

    parent = UnAuthorizedState
    auth_required = False

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_NAME_TEXT')
        send_async_message(self.bot, self.update, text, markup=None)

    @back_button
    def on_input(self, value):
        self.ctx.p_set_username(value)
        self.ctx.apply()
        self.new_state(RegisteringSexState)


class RegisteringSexState(BaseState):
    auth_required = False
    parent = RegisteringNameState

    def on_enter(self, text=None):
        if text is None:
            text = _('CHOOSE_SEX_TEXT')
        markup = telegram.ReplyKeyboardMarkup(
            [[
                telegram.KeyboardButton(_('MALE_BUTTON')),
                telegram.KeyboardButton(_('FEMALE_BUTTON')),
            ], [
                telegram.KeyboardButton(_('LABEL_BACK_BUTTON')),
            ]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        send_async_message(self.bot, self.update, text, markup=markup)

    @back_button
    def on_input(self, value):
        if value in [_('MALE_BUTTON'), _('FEMALE_BUTTON')]:
            sex_mapping = {
                _('MALE_BUTTON'): 1,
                _('FEMALE_BUTTON'): 0,
            }
            sex = sex_mapping[value]
            self.ctx.p_set_sex(sex)
            self.ctx.apply()
            self.new_state(RegisteringHeightState)


class RegisteringHeightState(BaseState):
    auth_required = False
    parent = RegisteringSexState

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_HEIGHT_TEXT')
        send_async_message(self.bot, self.update, text, markup=None)

    @back_button
    def on_input(self, value):
        self.ctx.p_set_height(value)
        self.ctx.apply()
        self.new_state(RegisteringWeightState)


class RegisteringWeightState(BaseState):
    auth_required = False
    parent = RegisteringHeightState

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_WEIGHT_TEXT')
        send_async_message(self.bot, self.update, text, markup=None)

    @back_button
    def on_input(self, value):
        self.ctx.p_set_weight(value)
        self.ctx.apply()
        self.new_state(RegisteringGoalState)

class RegisteringGoalState(BaseState):
    auth_required = False
    parent = RegisteringWeightState

    def on_enter(self, text=None):
        if text is None:
            text = _('CHOOSE_GOAL_TEXT')
        markup = telegram.ReplyKeyboardMarkup(
            [[
                telegram.KeyboardButton(_('LOST_WEIGHT_BUTTON')),
                telegram.KeyboardButton(_('GAIN_MUSCLE_MASS_BUTTON')),
            ], [
                telegram.KeyboardButton(_('SUPPORT_WEIGHT_BUTTON'))
            ],[
                telegram.KeyboardButton(_('LABEL_BACK_BUTTON'))
            ]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        send_async_message(self.bot, self.update, text, markup=markup)

    @back_button
    def on_input(self, value):
        if value in [_('LOST_WEIGHT_BUTTON'), _('GAIN_MUSCLE_MASS_BUTTON'), _('SUPPORT_WEIGHT_BUTTON')]:
            goal_mapping = {
                _('LOST_WEIGHT_BUTTON'): 0.8,
                _('SUPPORT_WEIGHT_BUTTON'): 1,
                _('GAIN_MUSCLE_MASS_BUTTON'): 1.2
            }
            goal_coeff = goal_mapping[value]
            self.ctx.p_set_goal(goal_coeff)
            self.ctx.apply()
            self.new_state(RegisteringLifestyleState)


class RegisteringLifestyleState(BaseState):
    auth_required = False
    parent = RegisteringGoalState

    def on_enter(self, text=None):
        if text is None:
            text = _('CHOOSE_LIFESTYLE_TEXT')
        markup = telegram.ReplyKeyboardMarkup(
            [[
                telegram.KeyboardButton(_('SEDENTARY_LIFESTYLE_BUTTON')),
            ], [
                telegram.KeyboardButton(_('EASY_ACTIVITY_BUTTON')),
            ], [
                telegram.KeyboardButton(_('AVERAGE_ACTIVITY_BUTTON')),
            ], [
                telegram.KeyboardButton(_('HIGH_ACTIVITY_BUTTON')),
            ], [
                telegram.KeyboardButton(_('VERY_HIGH_ACTIVITY_BUTTON'))
            ], [
                telegram.KeyboardButton(_('LABEL_BACK_BUTTON'))
            ]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        send_async_message(self.bot, self.update, text, markup=markup)

    @back_button
    def on_input(self, value):
        if value in [_('SEDENTARY_LIFESTYLE_BUTTON'), _('EASY_ACTIVITY_BUTTON'), _('AVERAGE_ACTIVITY_BUTTON'),
                     _('HIGH_ACTIVITY_BUTTON'), _('VERY_HIGH_ACTIVITY_BUTTON')]:
            lifestyle_mapping = {
                _('SEDENTARY_LIFESTYLE_BUTTON'): 1.2,
                _('EASY_ACTIVITY_BUTTON'): 1.375,
                _('AVERAGE_ACTIVITY_BUTTON'): 1.55,
                _('HIGH_ACTIVITY_BUTTON'): 1.725,
                _('VERY_HIGH_ACTIVITY_BUTTON'): 1.9
            }
            lifestyle_coeff = lifestyle_mapping[value]
            self.ctx.p_set_lifestyle(lifestyle_coeff)
            self.ctx.apply()
            self.new_state(RegisteringBirthYearState)

class RegisteringBirthYearState(BaseState):
    auth_required = False
    parent = RegisteringLifestyleState

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_BIRTH_YEAR_TEXT')
        send_async_message(self.bot, self.update, text, markup=None)

    @back_button
    def on_input(self, value):
        self.ctx.p_set_birth_year(value)
        self.ctx.p_set_authorized()
        self.ctx.p_get_username()
        z, z, name = self.ctx.apply()
        log.info(type(name))
        log.info(name)
        text = _('LOGGED_IN_TEXT')
        self.ctx.p_get_username()
        self.ctx.p_get_birth_year()
        self.ctx.p_get_weight()
        self.ctx.p_get_height()
        self.ctx.p_get_goal()
        self.ctx.p_get_lifestyle()
        self.ctx.p_get_sex()
        username, birth_year, weight, height, goal, lifestyle, sex = self.ctx.apply()
        age = datetime.today().year - int(birth_year)
        reg_params = {'name': username, 'sex': sex, 'weight': weight, 'height': height}
        norm = get_daily_rate(age, weight, height, goal, lifestyle, sex)
        log.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reg_user(reg_params)
        set_usernorm(username, norm)
        log.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        if name:
            text += ' ' + (_('LOGGED_IN_GREET_TEXT') % name)
        self.new_state(AuthorizedState, text=text)


class AuthorizedState(BaseState):
    parent = RegisteringBirthYearState
    auth_required = True

    def on_enter(self, text=None):
        if text is None:
            text = _('TOP_MENU_TEXT')
        markup = telegram.ReplyKeyboardMarkup(
            [[
                telegram.KeyboardButton(_('LABEL_ADD_NEW_DISH')),
                telegram.KeyboardButton(_('LABEL_ADD_DISH_EATEN'))
            ], [
                telegram.KeyboardButton(_('LABEL_TODAY_REPORT'))
            ]],
            resize_keyboard=True,
        )
        send_async_message(self.bot, self.update, text, markup=markup)

    def on_input(self, value):
        if value == _('LABEL_ADD_NEW_DISH'):
            self.new_state(AddDishState)
        elif value == _('LABEL_ADD_DISH_EATEN'):
            self.new_state(EatenDishState)
        elif value == _('LABEL_TODAY_REPORT'):
            self.new_state(DailyReportState)


class DailyReportState(BaseState):
    parent = AuthorizedState
    auth_required = True

    def on_enter(self, text=None):
        if text is None:
            pass
        self.ctx.p_get_username()
        username = self.ctx.apply()
        report = get_daily_report(username)[0]
        norm = get_daily_norm(username)
        msg = _('DAILY_REPORT_TEXT').format(r=report, n=norm)
        send_async_message(self.bot, self.update, msg, parse_mode=telegram.ParseMode.MARKDOWN)
        self.new_state(self.parent)


class AddDishState(BaseState):
    parent = AuthorizedState
    auth_required = True

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_DISH_TITLE')
        send_async_message(self.bot, self.update, text, parse_mode=telegram.ParseMode.MARKDOWN)

    def on_input(self, value):
        log.info(value)
        self.ctx.p_set_dish_title(value)
        self.ctx.apply()
        self.new_state(AddDishDescriptionState)


class AddDishDescriptionState(BaseState):
    parent = AddDishState
    auth_required = True

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_DISH_DESCRIPTION')
        send_async_message(self.bot, self.update, text, parse_mode=telegram.ParseMode.MARKDOWN)

    def on_input(self, value):
        self.ctx.p_get_dish_title()
        dish_title = self.ctx.apply()[0]
        try:
            add_new_dish(dish_title, value)
        except Exception:
            msg = _('ERROR_TEXT')
            send_async_message(self.bot, self.update, msg)
            self.new_state(AuthorizedState)
        else:
            self.new_state(AddDishIngrState_1)

types = get_ingredients_types()

class AddDishIngrState_1(BaseState):
    parent = AddDishDescriptionState
    auth_required = True

    types = get_ingredients_types()

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_INGREDIENT_TYPE')
        send_async_message(self.bot, self.update, text)
        msg = []
        for i, type_ in enumerate(self.types):
            msg.append('{}) {}'.format(i+1, type_))
        msg = '\n'.join(msg)
        send_async_message(self.bot, self.update, msg)


    def on_input(self, value):
        if value == _('END_RECIPE_BUTTON'):
            text = _('RECIPE_ADDED_TEXT')
            self.new_state(AuthorizedState, text=text)
        else:
            try:
                value = int(value) - 1
            except ValueError:
                send_async_message(self.bot, self.update, _('WRONG_VALUE_INT_EXPECTED'))
            else:
                if 0 <= value < len(self.types):
                    self.ctx.p_set_ingr_type(self.types[value])
                    self.ctx.apply()
                    ingredients = get_inrgediets_by_type(self.types[value])
                    msg = []
                    for i, ingredient in enumerate(ingredients):
                        msg.append('{}) {}'.format(i + 1, ingredient))
                    msg = '\n'.join(msg)
                    send_async_message(self.bot, self.update, msg)
                    self.new_state(AddDishIngrState_2)
                else:
                    send_async_message(self.bot, self.update, _('WRONG_VALUE_INT_EXPECTED'))


class AddDishIngrState_2(BaseState):
    parent = AddDishIngrState_1
    auth_required = True

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_INGR_NUM_AND_COUNT')
        markup = telegram.ReplyKeyboardMarkup(
            [[
                telegram.KeyboardButton(_('END_RECIPE_BUTTON')),
            ]],
            resize_keyboard=True,
        )
        send_async_message(self.bot, self.update, text, markup=markup)

    def on_input(self, value):
        if value == _('END_RECIPE_BUTTON'):
            text = _('RECIPE_ADDED_TEXT')
            self.new_state(AuthorizedState, text=text)
        else:
            try:
                ingr, amount = value.split(' ')
                ingr = int(ingr) - 1
                log.info(ingr)
                log.info(amount)
            except Exception:
                send_async_message(self.bot, self.update, _('WRONG_VALUE_INGR_AMOUNT_EXPECTED'))
            else:
                self.ctx.p_get_ingr_type()
                self.ctx.p_get_dish_title()
                ingr_type_i, dish = self.ctx.apply()
                ingredients = get_inrgediets_by_type(ingr_type_i)
                log.info('+'*11)
                log.info(dish)
                log.info(ingr)
                log.info(amount)
                add_di(dish, ingredients[ingr], amount)
                log.info(ingredients[ingr])
                log.info('+' * 11)
                self.new_state(self.parent, text=_('ADD_ANOTHER_INGR_OR_STOP_TEXT'))

class EatenDishState(BaseState):
    parent = AuthorizedState
    auth_required = True

    def on_enter(self, text=None):
        if text is None:
            text = _('INPUT_DISH_NAME')
        send_async_message(self.bot, self.update, text)


    def on_input(self, value):
        if is_dish_exist(value):
            d_features = calc_dish_features(value)
            self.ctx.p_get_username()
            username = self.ctx.apply()[0]
            curr_user_features = get_curr_user_features(username)
            c = {}
            c['calories'] = d_features['calories'] + curr_user_features['calories']
            c['proteins'] = d_features['proteins'] + curr_user_features['proteins']
            c['fats'] = d_features['fats'] + curr_user_features['fats']
            c['carbohydrates'] = d_features['carbohydrates'] + curr_user_features['carbohydrates']
            update_users_features(username, c)
            self.new_state(self.parent, text=_('DISH_EATEN_TEXT'))

        else:
            text = _('DISH_NOT_FOUND_TEXT')
            self.new_state(self.parent, text=text)



def reset_user_state(bot, update):
    ctx = Context(update.message.chat_id)
    ctx.p_get_username()
    username = ctx.apply()[0]
    delete_user(username)
    ctx.p_set_state('None', timeout=0)
    ctx.apply()
    BaseState(bot, update)
