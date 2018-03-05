import datetime
import telegram

from telegram_bot import main as main
from unittest import TestCase, mock
from unittest.mock import Mock

@mock.patch('builtins.print', Mock())
class TestMain(TestCase):

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_no_valid_messages(self, mock_bot):
        mock_bot.return_value.get_updates.return_value = []
        with self.assertRaises(SystemExit) as ex:
            main.main()
        self.assertEqual(1, ex.exception.code)
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)

    @mock.patch('builtins.input', Mock(side_effect=KeyboardInterrupt('Test Ctrl+C')))
    @mock.patch('telegram.Bot')
    def test_ctrl_c(self, mock_bot):
        mock_bot.return_value.get_updates.return_value = []
        with self.assertRaises(SystemExit) as ex:
            main.main()
        self.assertEqual(2, ex.exception.code)

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_valid_messages_single_user_bot_not_blocked(self, mock_bot):
        message = Mock()
        message.message = Mock()
        message.message.date = datetime.datetime.now()
        message.message.text = '/start'
        message.message.chat_id = 318448214
        message.message.chat.first_name = 'John'
        message.message.chat.last_name = 'Doe'
        mock_bot.return_value.get_updates.return_value = [message]
        main.main()
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)
        self.assertEqual(1, mock_bot.return_value.send_message.call_count)

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_valid_messages_single_user_bot_not_blocked_multiple_messages(self, mock_bot):
        message = Mock()
        message.message = Mock()
        message.message.date = datetime.datetime.now()
        message.message.text = '/start'
        message.message.chat_id = 318448214
        message.message.chat.first_name = 'John'
        message.message.chat.last_name = 'Doe'
        mock_bot.return_value.get_updates.return_value = [message, message, message]
        main.main()
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)
        self.assertEqual(1, mock_bot.return_value.send_message.call_count)

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_valid_messages_single_user_bot_blocked(self, mock_bot):
        message = Mock()
        message.message = Mock()
        message.message.date = datetime.datetime.now()
        message.message.text = '/start'
        message.message.chat_id = 318448214
        message.message.chat.first_name = 'John'
        message.message.chat.last_name = 'Doe'
        mock_bot.return_value.get_updates.return_value = [message]
        mock_bot.return_value.send_message.side_effect = telegram.error.Unauthorized('Test error.')
        with self.assertRaises(SystemExit) as ex:
            main.main()
        self.assertEqual(1, ex.exception.code)
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)
        self.assertEqual(1, mock_bot.return_value.send_message.call_count)

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_valid_messages_multiple_users_bot_not_blocked(self, mock_bot):
        message = Mock()
        message.message = Mock()
        message.message.date = datetime.datetime.now()
        message.message.text = '/start'
        message.message.chat_id = 318448214
        message.message.chat.first_name = 'John'
        message.message.chat.last_name = 'Doe'
        message2 = Mock()
        message2.message = Mock()
        message2.message.date = datetime.datetime.now()
        message2.message.text = '/start'
        message2.message.chat_id = 492444223
        message2.message.chat.first_name = 'Johnny'
        message2.message.chat.last_name = 'Appleseed'
        mock_bot.return_value.get_updates.return_value = [message, message2]
        main.main()
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)
        self.assertEqual(2, mock_bot.return_value.send_message.call_count)

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_valid_messages_multiple_users_bot_blocked_for_all_users(self, mock_bot):
        message = Mock()
        message.message = Mock()
        message.message.date = datetime.datetime.now()
        message.message.text = '/start'
        message.message.chat_id = 318448214
        message.message.chat.first_name = 'John'
        message.message.chat.last_name = 'Doe'
        message2 = Mock()
        message2.message = Mock()
        message2.message.date = datetime.datetime.now()
        message2.message.text = '/start'
        message2.message.chat_id = 492444223
        message2.message.chat.first_name = 'Johnny'
        message2.message.chat.last_name = 'Appleseed'
        mock_bot.return_value.get_updates.return_value = [message, message2]
        mock_bot.return_value.send_message.side_effect = telegram.error.Unauthorized('Test error.')
        with self.assertRaises(SystemExit) as ex:
            main.main()
        self.assertEqual(1, ex.exception.code)
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)
        self.assertEqual(2, mock_bot.return_value.send_message.call_count)

    @mock.patch('builtins.input', Mock())
    @mock.patch('telegram.Bot')
    def test_valid_messages_multiple_users_bot_blocked_for_some_users(self, mock_bot):
        message = Mock()
        message.message = Mock()
        message.message.date = datetime.datetime.now()
        message.message.text = '/start'
        message.message.chat_id = 318448214
        message.message.chat.first_name = 'John'
        message.message.chat.last_name = 'Doe'
        message2 = Mock()
        message2.message = Mock()
        message2.message.date = datetime.datetime.now()
        message2.message.text = '/start'
        message2.message.chat_id = 492444223
        message2.message.chat.first_name = 'Johnny'
        message2.message.chat.last_name = 'Appleseed'
        mock_bot.return_value.get_updates.return_value = [message, message2]
        mock_bot.return_value.send_message.side_effect = [telegram.error.Unauthorized('Test error.'), None]
        main.main()
        self.assertEqual(1, mock_bot.return_value.get_updates.call_count)
        self.assertEqual(2, mock_bot.return_value.send_message.call_count)