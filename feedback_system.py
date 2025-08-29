#!/usr/bin/env python3
"""
Система обратной связи для ML Router
Feedback System for ML Router Self-Learning
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from ml_router import ml_router

logger = logging.getLogger(__name__)

class FeedbackCollector:
    """Сбор обратной связи для улучшения ML Router"""
    
    def __init__(self):
        self.pending_feedback = {}  # message_id -> interaction_data
    
    def register_interaction(self, message_id: str, message: str, 
                           selected_agent: str, user_id: str) -> None:
        """Регистрация взаимодействия для последующей обратной связи"""
        self.pending_feedback[message_id] = {
            'message': message,
            'selected_agent': selected_agent,
            'user_id': user_id,
            'timestamp': datetime.now(),
            'session_id': f"session_{user_id}_{int(datetime.now().timestamp())}"
        }
    
    def collect_explicit_feedback(self, message_id: str, rating: int, 
                                 helpful: bool = True) -> bool:
        """Сбор явной обратной связи от пользователя (рейтинг 1-5)"""
        if message_id not in self.pending_feedback:
            logger.warning(f"No pending feedback for message_id: {message_id}")
            return False
        
        interaction = self.pending_feedback[message_id]
        
        # Записываем в ML Router
        success = ml_router.record_interaction(
            message=interaction['message'],
            selected_agent=interaction['selected_agent'],
            user_id=interaction['user_id'],
            session_id=interaction['session_id'],
            user_rating=rating,
            response_relevance=1.0 if helpful else 0.2
        )
        
        if success:
            logger.info(f"Recorded explicit feedback: rating={rating}, helpful={helpful}")
            del self.pending_feedback[message_id]
        
        return success
    
    def collect_implicit_feedback(self, message_id: str, 
                                follow_up_questions: int = 0,
                                conversation_continued: bool = True) -> bool:
        """Сбор неявной обратной связи на основе поведения пользователя"""
        if message_id not in self.pending_feedback:
            return False
        
        interaction = self.pending_feedback[message_id]
        
        # Вычисляем релевантность на основе поведения
        # Меньше дополнительных вопросов = лучше ответ
        relevance = max(0.1, 1.0 - (follow_up_questions * 0.2))
        
        # Если разговор продолжился естественно - это хороший знак
        if conversation_continued:
            relevance = min(1.0, relevance + 0.2)
        
        success = ml_router.record_interaction(
            message=interaction['message'],
            selected_agent=interaction['selected_agent'],
            user_id=interaction['user_id'],
            session_id=interaction['session_id'],
            response_relevance=relevance
        )
        
        if success:
            logger.info(f"Recorded implicit feedback: relevance={relevance:.2f}")
            del self.pending_feedback[message_id]
        
        return success

# Глобальный экземпляр
feedback_collector = FeedbackCollector()

def add_feedback_buttons_to_response(response: Dict[str, Any], message_id: str) -> Dict[str, Any]:
    """Добавляет кнопки обратной связи к ответу"""
    
    # Добавляем метаданные для фронтенда
    response['feedback'] = {
        'message_id': message_id,
        'rating_enabled': True,
        'like_dislike_enabled': True,
        'quick_feedback': [
            {'text': '👍', 'value': 'like', 'type': 'like'},
            {'text': '👎', 'value': 'dislike', 'type': 'dislike'},
            {'text': '🔄 Другой агент', 'value': 'wrong_agent', 'type': 'other'}
        ],
        'star_rating': {
            'enabled': True,
            'max_stars': 5,
            'placeholder': 'Оцените ответ'
        }
    }
    
    return response

def process_like_dislike_feedback(message_id: str, feedback_type: str, user_comment: str = None) -> bool:
    """Обработка лайк/дизлайк фидбека"""
    
    # Преобразуем лайк/дизлайк в рейтинг
    rating_map = {
        'like': 5,      # Лайк = 5 звезд
        'dislike': 1,   # Дизлайк = 1 звезда
        'wrong_agent': 2  # Неправильный агент = 2 звезды
    }
    
    helpful_map = {
        'like': True,
        'dislike': False,
        'wrong_agent': False
    }
    
    if message_id not in feedback_collector.pending_feedback:
        logger.warning(f"No pending feedback for message_id: {message_id}")
        return False
    
    rating = rating_map.get(feedback_type, 3)
    helpful = helpful_map.get(feedback_type, True)
    
    # Записываем основной фидбек
    success = feedback_collector.collect_explicit_feedback(
        message_id=message_id,
        rating=rating,
        helpful=helpful
    )
    
    # Если есть комментарий, сохраняем его отдельно
    if user_comment and success:
        try:
            interaction = feedback_collector.pending_feedback.get(message_id)
            if interaction:
                # Здесь можно добавить сохранение комментария в отдельную таблицу
                logger.info(f"User comment for {message_id}: {user_comment}")
        except Exception as e:
            logger.error(f"Failed to save user comment: {e}")
    
    return success