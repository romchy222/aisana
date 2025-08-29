#!/usr/bin/env python3
"""
API endpoints для системы обратной связи
Feedback API for ML Router Learning System
"""

import logging
from flask import Blueprint, request, jsonify
from feedback_system import feedback_collector

logger = logging.getLogger(__name__)

# Blueprint для API обратной связи
feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

@feedback_bp.route('/rate', methods=['POST'])
def rate_response():
    """Endpoint для оценки ответа пользователем"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        message_id = data.get('message_id')
        rating = data.get('rating')  # 1-5 stars
        helpful = data.get('helpful', True)  # boolean
        
        if not message_id:
            return jsonify({'success': False, 'error': 'message_id required'}), 400
        
        if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
            return jsonify({'success': False, 'error': 'Rating must be 1-5'}), 400
        
        # Record feedback
        success = feedback_collector.collect_explicit_feedback(
            message_id=message_id,
            rating=rating if rating is not None else (5 if helpful else 1),
            helpful=helpful
        )
        
        if success:
            logger.info(f"Collected feedback for message {message_id}: rating={rating}, helpful={helpful}")
            return jsonify({'success': True, 'message': 'Спасибо за оценку!'})
        else:
            return jsonify({'success': False, 'error': 'Failed to record feedback'}), 500
            
    except Exception as e:
        logger.error(f"Error in rate_response: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/quick', methods=['POST'])
def quick_feedback():
    """Endpoint для быстрой обратной связи (кнопки лайк/дизлайк)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        message_id = data.get('message_id')
        feedback_type = data.get('feedback_type')  # 'like', 'dislike', 'wrong_agent'
        user_comment = data.get('comment', '')  # Опциональный комментарий
        
        if not message_id or not feedback_type:
            return jsonify({'success': False, 'error': 'message_id and feedback_type required'}), 400
        
        # Импортируем функцию обработки
        from feedback_system import process_like_dislike_feedback
        
        success = process_like_dislike_feedback(message_id, feedback_type, user_comment)
        
        if success:
            messages = {
                'like': 'Спасибо за лайк! 👍',
                'dislike': 'Спасибо за отзыв! Мы работаем над улучшением. 👎',
                'wrong_agent': 'Спасибо! Мы научим систему лучше выбирать агентов. 🔄'
            }
            return jsonify({
                'success': True, 
                'message': messages.get(feedback_type, 'Спасибо за отзыв!')
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to record feedback'}), 500
            
    except Exception as e:
        logger.error(f"Error in quick_feedback: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/like-dislike', methods=['POST'])
def like_dislike_feedback():
    """Отдельный endpoint специально для лайк/дизлайк"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        message_id = data.get('message_id')
        is_like = data.get('is_like')  # True для лайка, False для дизлайка
        comment = data.get('comment', '')
        
        if not message_id or is_like is None:
            return jsonify({'success': False, 'error': 'message_id and is_like required'}), 400
        
        feedback_type = 'like' if is_like else 'dislike'
        
        # Импортируем функцию обработки
        from feedback_system import process_like_dislike_feedback
        
        success = process_like_dislike_feedback(message_id, feedback_type, comment)
        
        if success:
            message = 'Спасибо за лайк! 👍' if is_like else 'Спасибо за дизлайк! Мы учтем ваш отзыв. 👎'
            return jsonify({
                'success': True, 
                'message': message,
                'feedback_recorded': True
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to record feedback'}), 500
            
    except Exception as e:
        logger.error(f"Error in like_dislike_feedback: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/implicit', methods=['POST'])
def implicit_feedback():
    """Endpoint для неявной обратной связи (поведенческие метрики)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        message_id = data.get('message_id')
        follow_up_questions = data.get('follow_up_questions', 0)
        conversation_continued = data.get('conversation_continued', True)
        
        if not message_id:
            return jsonify({'success': False, 'error': 'message_id required'}), 400
        
        success = feedback_collector.collect_implicit_feedback(
            message_id=message_id,
            follow_up_questions=follow_up_questions,
            conversation_continued=conversation_continued
        )
        
        if success:
            logger.info(f"Collected implicit feedback for message {message_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to record feedback'}), 500
            
    except Exception as e:
        logger.error(f"Error in implicit_feedback: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/stats', methods=['GET'])
def get_feedback_stats():
    """Получение статистики обучения ML Router"""
    try:
        from ml_router import ml_router
        
        stats = ml_router.get_learning_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500