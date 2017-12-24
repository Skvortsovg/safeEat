# -*- coding: utf-8 -*-

import os
import gettext


this_dir = os.path.abspath(os.path.dirname(__file__))
locales_dir = os.path.join(this_dir, '..', 'locale')

langs = dict(
    ru=gettext.translation('safeeat', locales_dir, languages=['ru']),
)
