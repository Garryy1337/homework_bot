class StatusCodeError(Exception):
    """
    Исключение, возникающее при.
      получении ответа с некорректным HTTP-статус-кодом.
    """

    def __init__(self, status_code):
        """Конструктор класса."""
        self.status_code = status_code

    def __str__(self):
        """Возвращает строковое представление исключения."""
        return f"Status code is different from 200: {self.status_code}"
