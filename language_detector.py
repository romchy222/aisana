"""
Автоматическое определение языка сообщения пользователя
Language detection for automatic response language selection
"""

import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class LanguageDetector:
    """Класс для определения языка текста"""
    
    def __init__(self):
        # Паттерны для определения языков
        self.language_patterns = {
            'ru': {
                'keywords': [
                    'как', 'что', 'где', 'когда', 'почему', 'который', 'какой', 'кто',
                    'может', 'можно', 'нужно', 'должен', 'хочу', 'хочется', 'буду',
                    'университет', 'поступление', 'документы', 'экзамен', 'студент',
                    'общежитие', 'стипендия', 'факультет', 'специальность', 'диплом',
                    'работа', 'карьера', 'вакансия', 'трудоустройство', 'резюме',
                    'помощь', 'вопрос', 'ответ', 'информация', 'сведения'
                ],
                'chars': 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                'stopwords': ['и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'о']
            },
            'kz': {
                'keywords': [
                    'қалай', 'не', 'қайда', 'қашан', 'неге', 'қай', 'кім', 'қандай',
                    'болады', 'бола', 'керек', 'тиіс', 'қалаймын', 'болам', 'еді',
                    'университет', 'түсу', 'құжаттар', 'емтихан', 'студент',
                    'жатақхана', 'шәкіақы', 'факультет', 'мамандық', 'диплом',
                    'жұмыс', 'мансап', 'бос', 'жұмысқа', 'резюме', 'өмірбаян',
                    'көмек', 'сұрақ', 'жауап', 'ақпарат', 'мәлімет'
                ],
                'chars': 'абвгғдеёжзийкқлмнңопрстуүұфхһцчшщъыіьэюя',
                'stopwords': ['және', 'мен', 'бен', 'пен', 'үшін', 'дейін', 'бойынша', 'туралы']
            },
            'en': {
                'keywords': [
                    'how', 'what', 'where', 'when', 'why', 'which', 'who', 'whom',
                    'can', 'could', 'should', 'would', 'will', 'want', 'need',
                    'university', 'admission', 'documents', 'exam', 'student',
                    'dormitory', 'scholarship', 'faculty', 'specialty', 'diploma',
                    'work', 'career', 'job', 'employment', 'resume', 'cv',
                    'help', 'question', 'answer', 'information', 'details'
                ],
                'chars': 'abcdefghijklmnopqrstuvwxyz',
                'stopwords': ['and', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from']
            }
        }
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Определяет язык текста
        Возвращает: (код_языка, уверенность)
        """
        if not text or len(text.strip()) < 2:
            return 'ru', 0.5  # По умолчанию русский
        
        text = text.lower().strip()
        scores = {'ru': 0.0, 'kz': 0.0, 'en': 0.0}
        
        # Проверяем символы
        for lang, patterns in self.language_patterns.items():
            char_score = self._calculate_char_score(text, patterns['chars'])
            scores[lang] += char_score * 0.4
        
        # Проверяем ключевые слова
        for lang, patterns in self.language_patterns.items():
            keyword_score = self._calculate_keyword_score(text, patterns['keywords'])
            scores[lang] += keyword_score * 0.6
        
        # Находим язык с максимальным счетом
        best_language = max(scores, key=scores.get)
        confidence = scores[best_language]
        
        # Если уверенность слишком низкая, возвращаем русский по умолчанию
        if confidence < 0.2:
            return 'ru', 0.5
        
        logger.info(f"Detected language: {best_language} (confidence: {confidence:.2f}) for text: '{text[:50]}...'")
        return best_language, confidence
    
    def _calculate_char_score(self, text: str, lang_chars: str) -> float:
        """Подсчитывает долю символов языка в тексте"""
        if not text:
            return 0.0
        
        lang_char_count = sum(1 for char in text if char in lang_chars)
        total_alpha_chars = sum(1 for char in text if char.isalpha())
        
        if total_alpha_chars == 0:
            return 0.0
        
        return lang_char_count / total_alpha_chars
    
    def _calculate_keyword_score(self, text: str, keywords: list) -> float:
        """Подсчитывает долю ключевых слов языка в тексте"""
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0
        
        keyword_matches = sum(1 for word in words if word in keywords)
        return keyword_matches / len(words)
    
    def get_language_name(self, lang_code: str) -> str:
        """Возвращает название языка по коду"""
        names = {
            'ru': 'Русский',
            'kz': 'Қазақша',
            'en': 'English'
        }
        return names.get(lang_code, 'Русский')

# Глобальный экземпляр детектора
language_detector = LanguageDetector()