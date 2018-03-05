import datetime

import telegram

from telegram_bot.config.config import TELEGRAM_CONFIG


def bold(msg: str) -> str:
    """
        Given an 'str' object, wraps it between ANSI bold escape characters.
        :param msg: Message to be wrapped.
        :return: The same message, which will be displayed as bold by the terminal.
    """
    return '\u001b[1m%s\u001b[0m' % msg


def red_bold(msg: str) -> str:
    """
        Given an 'str' object, wraps it between ANSI red & bold escape characters.
        :param msg: Message to be wrapped.
        :return: The same message, which will be displayed as red & bold by the terminal.
    """
    return '\u001b[1;31m%s\u001b[0m' % msg


def green_bold(msg: str) -> str:
    """
        Given an 'str' object, wraps it between ANSI green & bold escape characters.
        :param msg: Message to be wrapped.
        :return: The same message, which will be displayed as green & bold by the terminal.
    """
    return '\u001b[1;32m%s\u001b[0m' % msg


def yellow_bold(msg: str) -> str:
    """
        Given an 'str' object, wraps it between ANSI yellow & bold escape characters.
        :param msg: Message to be wrapped.
        :return: The same message, which will be displayed as yellow & bold by the terminal.
    """
    return '\u001b[1;33m%s\u001b[0m' % msg


def blue_bold(msg: str) -> str:
    """
        Given an 'str' object, wraps it between ANSI blue & bold escape characters.
        :param msg: Message to be wrapped.
        :return: The same message, which will be displayed as blue & bold by the terminal.
    """
    return '\u001b[1;34m%s\u001b[0m' % msg


def main():
    # Waiting until the user has established a conversation with the bot.
    try:
        input('%s\nHit "%s" when done:' % (
            'Start a chat with the Telegram bot %s.' % blue_bold(TELEGRAM_CONFIG['BOT_NAME']), bold('Enter')))
    except KeyboardInterrupt:
        print('\n\nAborting installation (Ctrl+C).')
        exit(2)

    # Fetching bot's latest messages
    bot = telegram.Bot(token=TELEGRAM_CONFIG['TOKEN'])
    messages = bot.get_updates(timeout=TELEGRAM_CONFIG['TIMEOUT'], allowed_updates=['message'])
    now = datetime.datetime.now() + datetime.timedelta(seconds=-TELEGRAM_CONFIG['MAX_VALID_TIME'])
    # Filtering by recent messages containing "/start"
    valid_messages = [x.message for x in messages if x.message.date > now and x.message.text == '/start']
    # No valid messages: exiting
    if not valid_messages:
        print('\n%s' % red_bold('The bot hasn\'t received recent messages. Did you start the chat with the bot?'))
        print('%s If you already have an open chat with the bot, you can either send it %s, or %s the chat '
              'and %s a new one.' % (yellow_bold('Hint:'), blue_bold('/start'), bold('remove'), bold('start')))
        exit(1)
    # One or more valid messages have been found
    else:
        blocked_users = 0
        metainfo = set([(x.chat_id, x.chat.first_name + ' ' + x.chat.last_name) for x in valid_messages])
        template_message = '*%s*, your `CHAT_ID` is: %d\nYou must now configure the *Climate Change App* with ' \
                           'this `CHAT_ID`.\n  👉 Click [here](%s) if you don\'t know how to do it.'
        for entry in metainfo:
            try:
                message = template_message % (entry[1], entry[0], TELEGRAM_CONFIG['TELEGRAM_DOCS_URL'])
                bot.send_message(chat_id=entry[0], text=message, parse_mode=telegram.ParseMode.MARKDOWN)
            except telegram.error.Unauthorized:
                print('%s User %s has blocked the bot, so he/she cannot receive messages.' % (
                    yellow_bold('Warning:'), bold(entry[1])))
                blocked_users += 1
        if blocked_users == len(metainfo):
            message = 'All users have blocked the bot, so they cannot receive messages from it!' if \
                    blocked_users > 1 else 'The user has blocked the bot, so he/she cannot receive messages from it!'
            print('%s' % red_bold(message))
            print('%s If you delete the chat with the bot, don\'t use the %s option, but %s (otherwise, you\'ll %s '
                  'the incoming messages from the bot!).' % (
                  yellow_bold('IMPORTANT:'), bold('Delete and Stop'), bold('Delete'), red_bold('block')))
            exit(1)
        print('\n%s You should have received a message from the bot.' % green_bold('>'))
        print('\nNow, you need to configure the %s with the %s you have received.\n%s If you don\'t know how to do '
              'it, check it out the docs, available here: %s' % (
                  bold('Climate Change App'), blue_bold('CHAT_ID'), yellow_bold('Hint:'),
                  TELEGRAM_CONFIG['TELEGRAM_DOCS_URL']))
        print('%s If you delete the chat with the bot, don\'t use the %s option, but %s (otherwise, you\'ll %s '
              'the incoming messages from the bot!).' %
              (yellow_bold('IMPORTANT:'), bold('Delete and Stop'), bold('Delete'), red_bold('block')))


if __name__ == '__main__':
    print('%s Using Climate Change App Telegram Bot configurator %s.\n' % (
        green_bold('>'), bold(TELEGRAM_CONFIG['TELEGRAM_CONFIGURATOR_VERSION'])))
    main()
