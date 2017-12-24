#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import optparse
import re
from datetime import datetime, timedelta
import time



def start_bot():
    from bot import updater
    updater.start_polling()
    updater.idle()


def start_daemon():
    import daemon
    class config:
        gid = 20
        uid = 501
        pid_dir = ''
        pid_name = 'safeeat.pid'
        config_filename = 'conf'

    with daemon.Daemonize(config):
        start_bot()
        # from bot import updater
        # updater.start_polling()
        # updater.idle()





def run():
    appname = 'safeeat'
    usage = '%prog'
    __version__ = '0.0.1'
    description = 'Description'
    epilog = 'Epilog'

    parser = optparse.OptionParser(
        prog=appname,
        usage=usage,
        version=__version__,
        description=description,
        epilog=epilog
    )
    parser.add_option(
        '--run',
        help='Start bot',
        action='store_true',
        default=False
    )
    parser.add_option(
        '--d',
        help='Start demon',
        action='store_true',
        default=False
    )
    opts, args = parser.parse_args(sys.argv[1:])

    if opts.d is True:
        start_daemon()
    elif opts.run is True:
        start_bot()


if __name__ == '__main__':
    run()
