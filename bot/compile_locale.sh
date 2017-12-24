#!/bin/bash
. /Users/skv/Documents/safeEat/bot/venv/bin/activate
if [ -r ./locale/ru/LC_MESSAGES/safeeat.po ]; then
    # msgfmt.py \
    msgfmt \
        -o ./locale/ru/LC_MESSAGES/safeeat.mo \
        ./locale/ru/LC_MESSAGES/safeeat.po
fi
deactivate
