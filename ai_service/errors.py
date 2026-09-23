"""Stable public errors; provider details must never enter API responses."""
ERRORS = {
    'invalid_request': (422, 'Запрос не соответствует контракту. Проверьте поля, типы и ограничения в /docs.'),
    'ai_not_configured': (503, 'Для консультанта не настроены API-ключ или модель.'),
    'ai_unavailable': (503, 'ИИ временно недоступен. Повторите запрос позже.'),
    'ai_timeout': (504, 'Превышено время ожидания ответа ИИ.'),
    'invalid_ai_response': (502, 'ИИ вернул неполный ответ или ответ неверного формата.'),
    'ai_refusal': (502, 'ИИ отказался формировать ответ на этот запрос.'),
}


class AIError(Exception):
    def __init__(self, code: str):
        self.code = code
        self.status_code, self.public_message = ERRORS[code]
        super().__init__(code)

    def payload(self) -> dict:
        return {'error': {'code': self.code, 'message': self.public_message}}
