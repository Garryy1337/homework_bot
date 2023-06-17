import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import StatusCodeError, TelegramAPIError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных окружения."""
    vars = [TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN]
    if not all(vars):
        logging.critical(
            f'Отсутствует обязательная переменная окружения: {vars}')
        return False
    return True


def get_api_answer(timestamp):
    """
    Запрос к эндпоинту.
    В случае успеха возвращает ответ API, приведенный к типам данных Python.
    """
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if response.status_code != 200:
            raise StatusCodeError(
                f'Status code is different from 200 : {response.status_code}'
            )
        return response.json()
    except requests.RequestException():
        logging.error('Endpoint not available')
        return None
    except Exception as error:
        logging.error(f'Endpoint request error: {error}')


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        logging.error('Некорректный ответ API: %s', response)
        raise TypeError('Некорректный ответ API')
    if 'homeworks' not in response:
        logging.error('Некорректный ответ API: %s', response)
        raise TelegramAPIError('''Некорректный ответ API:
          отсутствует ключ "homeworks" ''')
    if not isinstance(response['homeworks'], list):
        logging.error('Некорректный ответ API: %s', response)
        raise TypeError('''Некорректный ответ API:
          значение ключа "homeworks" должно быть списком''')
    return True


def parse_status(homework):
    """Извлечение статуса работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        logging.error('Не найден ключ "homework_name" в ответе API')
        raise KeyError('Не найден ключ "homework_name" в ответе API')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logging.error('Неизвестный статус: %s', status)
        raise TelegramAPIError('Неизвестный статус: %s' % status)
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение успешно отправлено в Telegram: {message}')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправке сообщения в Telegram: {error}')
        raise TelegramAPIError('Ошибка при отправке сообщения в Telegram')


def main():
    """Основная логика работы бота."""
    # Logging
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Проверка доступности переменных окружения
    if not check_tokens():
        sys.exit(1)

    # Инициализация бота
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    # Начальная временная метка
    timestamp = int(time.time())

    while True:
        try:
            # Запрос к API
            response = get_api_answer(timestamp)

            # Проверка ответа API
            if not check_response(response):
                continue

            # Изменение статусов проверки работ
            for homework in response['homeworks']:
                status_message = parse_status(homework)
                if status_message:
                    send_message(bot, status_message)

            # Обновление временной метки
            timestamp = response['current_date']

            # Пауза между запросами
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            logging.error(f'Ошибка: {error}')

        finally:
            # Пауза перед следующим запросом
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
