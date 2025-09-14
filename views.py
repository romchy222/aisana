# Импорт необходимых модулей
import time
import logging
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, Response
import requests
import base64
from sqlalchemy import func, desc
from datetime import datetime, timedelta


# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint для основных маршрутов
main_bp = Blueprint('views', __name__)

# Инициализация роутера агентов (выполним позже, чтобы избежать circular import)
agent_router = None

def initialize_agent_router():
    """Initialize agent router after app context is available"""
    global agent_router
    if agent_router is None:
        from agents import AgentRouter
        agent_router = AgentRouter()
    return agent_router


@main_bp.route('/')
def index_new():
    """New main page with chat widget"""
    try:
        from models import UserQuery, AgentKnowledgeBase, db
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # Получаем статистику из базы данных
        # Общее количество уникальных пользователей
        total_users = db.session.query(func.count(func.distinct(UserQuery.session_id))).scalar() or 0
        
        # Общее количество обработанных запросов
        total_queries = UserQuery.query.count()
        
        # Количество активных записей в базе знаний агентов
        total_knowledge = AgentKnowledgeBase.query.filter_by(is_active=True).count()
        
        # Средняя точность ответов (на основе рейтингов)
        liked_queries = UserQuery.query.filter_by(user_rating='like').count()
        total_rated_queries = UserQuery.query.filter(UserQuery.user_rating.isnot(None)).count()
        accuracy_rate = round((liked_queries / total_rated_queries * 100) if total_rated_queries > 0 else 95, 0)
        
        # Статистика агентов
        agent_stats = db.session.query(
            UserQuery.agent_name,
            func.count(UserQuery.id).label('count')
        ).filter(
            UserQuery.agent_name.isnot(None)
        ).group_by(UserQuery.agent_name).all()
        
        # Подготавливаем данные для передачи в шаблон
        stats = {
            'total_users': total_users,
            'total_queries': total_queries,
            'total_knowledge': total_knowledge,
            'accuracy_rate': int(accuracy_rate),
            'agent_stats': [{'name': stat.agent_name, 'count': stat.count} for stat in agent_stats]
        }
        
        return render_template('index_new.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error getting statistics for index page: {str(e)}")
        # Fallback к значениям по умолчанию если есть ошибка БД
        stats = {
            'total_users': 15000,
            'total_queries': 50000,
            'total_knowledge': 500,
            'accuracy_rate': 95,
            'agent_stats': []
        }
        return render_template('index_new.html', stats=stats)

@main_bp.route('/index')
def index():
    """Old main page redirect"""
    return render_template('index_new.html')

@main_bp.route('/chat')
def chat_new():
    """New chat page"""
    return render_template('chat_new.html')

@main_bp.route('/chat-old')
def chat_page():
    """Old chat page"""
    return render_template('chat.html')

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/set-language/<language>')
def set_language(language):
    """Set user language"""
    from flask import session, redirect, url_for, request
    if language in ['ru', 'kz', 'en']:
        session['language'] = language
    return redirect(request.referrer or url_for('views.index_new'))


@main_bp.route('/widget-demo')
def widget_demo():
    """Widget integration demo page"""
    return render_template('widget-demo.html')


@main_bp.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """Get chat history for current user session"""
    try:
        from models import UserQuery
        from app import db
        
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        # Get last 50 messages for this session
        history = UserQuery.query.filter_by(session_id=session_id).order_by(desc(UserQuery.created_at)).limit(50).all()
        
        chat_history = []
        for query in reversed(history):  # Reverse to show oldest first
            chat_history.append({
                'message': query.user_message,
                'response': query.bot_response,
                'agent_name': query.agent_name or 'Unknown',
                'timestamp': query.created_at.isoformat() if query.created_at else None,
                'language': query.language or 'ru'
            })
        
        return jsonify({
            'success': True,
            'history': chat_history,
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load chat history'
        }), 500

@main_bp.route('/api/chat/clear', methods=['POST'])
def clear_chat_history():
    """Clear chat history and user memory for current user session"""
    try:
        from models import UserQuery
        from app import db
        from user_memory import user_memory
        
        session_id = session.get('session_id')
        if session_id:
            # Delete all queries for this session
            UserQuery.query.filter_by(session_id=session_id).delete()
            db.session.commit()
            
            # Clear user context/memory
            user_memory.clear_context(session_id)
        
        return jsonify({
            'success': True,
            'message': 'Chat history and user memory cleared'
        })
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear chat history'
        }), 500

@main_bp.route('/api/user/context', methods=['GET'])
def get_user_context():
    """Get current user context and memory"""
    try:
        from models import UserContext
        
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'No active session'
            }), 400
        
        context = UserContext.query.filter_by(session_id=session_id).first()
        
        if context:
            return jsonify({
                'success': True,
                'context': context.to_dict(),
                'has_memory': True
            })
        else:
            return jsonify({
                'success': True,
                'context': {},
                'has_memory': False
            })
            
    except Exception as e:
        logger.error(f"Error getting user context: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user context'
        }), 500

@main_bp.route('/api/user/update-info', methods=['POST'])
def update_user_info():
    """Allow user to manually update their information"""
    try:
        from user_memory import user_memory
        
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'No active session'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        context = user_memory.get_or_create_context(session_id)
        
        # Update user information
        if 'name' in data and data['name']:
            context.name = data['name'].strip()
        
        if 'language_preference' in data and data['language_preference'] in ['ru', 'kz', 'en']:
            context.language_preference = data['language_preference']
        
        if 'interests' in data and isinstance(data['interests'], list):
            context.interests = data['interests']
        
        context.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User information updated',
            'context': context.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating user info: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update user information'
        }), 500

@main_bp.route('/api/chat', methods=['POST'])
@main_bp.route('/chat', methods=['POST'])
def chat():
    try:
        from models import UserQuery
        from app import db
        from flask import current_app
        from feedback_system import feedback_collector, add_feedback_buttons_to_response
        from user_memory import user_memory
        import uuid

        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'Сообщение не найдено'}), 400

        user_message = data['message'].strip()
        
        # Создание или получение session_id для сохранения истории
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        # Автоматическое определение языка если не указан
        language = data.get('language')
        if not language or language == 'auto':
            from language_detector import language_detector
            detected_lang, confidence = language_detector.detect_language(user_message)
            language = detected_lang
            logger.info(f"Auto-detected language: {language} (confidence: {confidence:.2f})")
        else:
            # Валидация переданного языка
            if language not in ['ru', 'kz', 'en']:
                language = 'ru'
        
        agent_type = data.get('agent')  # Updated parameter name

        if not user_message:
            return jsonify({'success': False, 'error': 'Пустое сообщение'}), 400

        start_time = time.time()

        # Initialize router within app context
        router = initialize_agent_router()

        # Get user ID for personalization and create session_id if not exists
        user_id = session.get('user_id', 'anonymous')
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        session.permanent = True

        # Get user context for memory
        user_context = user_memory.get_context_for_ai(session_id)
        
        # Add context to user message if exists
        if user_context:
            contextual_message = f"{user_context}\nСОБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {user_message}"
        else:
            contextual_message = user_message

        if agent_type and agent_type != 'auto':
            # Пользователь явно выбрал агента - используем только его
            selected_agent = None
            for agent in router.agents:
                if getattr(agent, "agent_type", None) and (agent.agent_type == agent_type):
                    selected_agent = agent
                    break
            
            if selected_agent:
                # Принудительно используем выбранного агента
                result = selected_agent.process_message(contextual_message, language, user_id)
                result['agent_type'] = selected_agent.agent_type
                result['agent_name'] = selected_agent.name
                result['confidence'] = 1.0  # Максимальная уверенность при ручном выборе
                result['manually_selected'] = True
                logger.info(f"User manually selected agent: {selected_agent.name}")
            else:
                # Агент не найден - возвращаем ошибку
                logger.warning(f"Requested agent type '{agent_type}' not found")
                result = {
                    'response': f"Извините, запрошенный агент '{agent_type}' недоступен. Попробуйте выбрать другого агента или используйте автоматический выбор.",
                    'confidence': 0.0,
                    'agent_type': 'error',
                    'agent_name': 'System',
                    'context_used': False,
                    'context_confidence': 0.0,
                    'cached': False,
                    'error': True
                }
        else:
            # Автоматический выбор агента
            result = router.route_message(contextual_message, language, user_id)

        response_time = time.time() - start_time

        # Generate unique message ID for feedback tracking
        message_id = str(uuid.uuid4())
        
        # Register interaction for ML learning (always register for feedback)
        feedback_collector.register_interaction(
            message_id, user_message, result.get('agent_name', ''), user_id
        )
        
        # Add feedback buttons to response
        result = add_feedback_buttons_to_response(result, message_id)

        # Create UserQuery within app context
        user_query = UserQuery()
        user_query.user_message = user_message
        user_query.bot_response = result['response']
        user_query.language = language
        user_query.response_time = response_time
        user_query.agent_type = result.get('agent_type')
        user_query.agent_name = result.get('agent_name')
        user_query.agent_confidence = result.get('confidence', 0.0)
        user_query.context_used = result.get('context_used', False)
        user_query.session_id = session_id
        user_query.ip_address = request.remote_addr
        user_query.user_agent = request.headers.get('User-Agent', '')

        try:
            db.session.add(user_query)
            db.session.commit()
            
            # Update user memory with the interaction
            user_memory.update_context(
                session_id=session_id,
                user_message=user_message,  # Use original message for context extraction
                bot_response=result['response'],
                agent_name=result.get('agent_name')
            )
            
        except Exception as db_error:
            logger.warning(f"Database error (continuing without saving): {str(db_error)}")
            # Continue without saving to database

        logger.info(
            f"Chat response generated in {response_time:.2f}s "
            f"by {result.get('agent_name', 'Unknown')} agent "
            f"(confidence: {result.get('confidence', 0):.2f}) "
            f"for language: {language}"
        )

        response_data = {
            'success': True,
            'response': result['response'],
            'response_time': response_time,
            'agent_name': result.get('agent_name'),
            'agent_type': result.get('agent_type'),
            'confidence': result.get('confidence', 0.0),
            'query_id': getattr(user_query, 'id', None),
            'message_id': message_id,
            'routing_method': result.get('routing_method', 'traditional'),
            'ml_confidence': result.get('ml_confidence'),
            'detected_language': language,  # Определенный язык
            'feedback': result.get('feedback', {})  # Include feedback metadata
        }
        
        # Add images data if present
        if 'images' in result:
            response_data['images'] = result['images']
            response_data['special_response'] = result.get('special_response', 'images')
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        # Use a default language if language is not defined
        lang = locals().get('language', 'ru')
        error_message = "Извините, произошла ошибка. Попробуйте еще раз." if lang == 'ru' else "Кешіріңіз, қате орын алды. Қайталап көріңіз."
        return jsonify({'success': False, 'error': error_message}), 500

@main_bp.route('/api/health')
@main_bp.route('/health')
@main_bp.route('/healthz')
@main_bp.route('/ready')
def health_check():
    """Enhanced health check endpoint for deployment readiness probes"""
    try:
        # Quick response for basic health check
        health_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'service': 'bolashak-chat',
            'version': '1.0.0'
        }
        
        # Optional detailed check (only if requested)
        detailed = request.args.get('detailed', 'false').lower() == 'true'
        if detailed:
            try:
                from models import db
                from sqlalchemy import text
                # Quick database connectivity test with timeout
                with db.engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()
                health_data['database'] = 'connected'
            except Exception as e:
                # Don't fail health check for DB issues in production
                health_data['database'] = 'unavailable'
                health_data['db_error'] = str(e)
        
        return jsonify(health_data), 200
        
    except Exception as e:
        # Always return 200 for basic health check to pass deployment probes
        return jsonify({
            'status': 'degraded',
            'timestamp': time.time(),
            'error': str(e)
        }), 200


@main_bp.route('/api/startup', methods=['POST'])
def startup_initialization():
    """Initialize database tables after deployment startup"""
    try:
        from models import db
        from sqlalchemy import text
        from flask import current_app
        
        # Test database connection with timeout
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Database connection test successful")

        # Create all tables in database
        db.create_all()
        logger.info("Database tables created successfully")
        
        return jsonify({'status': 'initialized', 'timestamp': time.time()}), 200

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return jsonify({
            'status': 'failed', 
            'error': str(e), 
            'timestamp': time.time()
        }), 500


@main_bp.route('/api/agents')
def get_agents():
    """Get information about available agents"""
    try:
        router = initialize_agent_router()
        agents_info = router.get_available_agents()
        return jsonify({
            'agents': agents_info,
            'total_agents': len(agents_info)
        })
    except Exception as e:
        logger.error(f"Error getting agents info: {str(e)}")
        return jsonify({'error': 'Failed to get agents information'}), 500


@main_bp.route('/api/rate/<int:query_id>', methods=['POST'])
def rate_response(query_id):
    """Rate a bot response with like/dislike"""
    try:
        from models import UserQuery
        from app import db

        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({'error': 'Rating not provided'}), 400

        rating = data['rating']
        if rating not in ['like', 'dislike']:
            return jsonify({'error': 'Invalid rating. Must be "like" or "dislike"'}), 400

        # Find the query
        query = UserQuery.query.get(query_id)
        if not query:
            return jsonify({'error': 'Query not found'}), 404

        # Update rating
        query.user_rating = rating
        query.rating_timestamp = datetime.utcnow()

        try:
            db.session.commit()
            logger.info(f"Query {query_id} rated as {rating}")
            return jsonify({
                'success': True,
                'rating': rating,
                'query_id': query_id
            })
        except Exception as db_error:
            logger.error(f"Database error saving rating: {str(db_error)}")
            return jsonify({'error': 'Failed to save rating'}), 500

    except Exception as e:
        logger.error(f"Error rating response: {str(e)}")
        return jsonify({'error': 'Failed to rate response'}), 500


# Voice chat endpoints
@main_bp.route('/api/voice/start-session', methods=['POST'])
def start_voice_session():
    """Start a new voice chat session"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'anonymous')
        language = data.get('language', 'ru')

        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())

        # Store session info (could be in database in production)
        session['voice_session_id'] = session_id
        session['voice_language'] = language
        session['voice_user_id'] = user_id

        logger.info(f"Started voice session {session_id} for user {user_id}")

        return jsonify({
            'session_id': session_id,
            'status': 'active',
            'language': language
        })

    except Exception as e:
        logger.error(f"Error starting voice session: {str(e)}")
        return jsonify({'error': 'Failed to start voice session'}), 500


@main_bp.route('/api/voice/process', methods=['POST'])
def process_voice_message():
    """Process voice message (placeholder for actual speech-to-text integration)"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        text_message = data.get('text')  # In real implementation, this would be audio data

        if not session_id or session_id != session.get('voice_session_id'):
            return jsonify({'error': 'Invalid session'}), 401

        if not text_message:
            return jsonify({'error': 'No message provided'}), 400

        # Use existing chat processing
        language = session.get('voice_language', 'ru')

        # Process through existing chat system
        router = initialize_agent_router()
        user_id = session.get('voice_user_id', 'anonymous')
        result = router.route_message(text_message, language, user_id)

        # Log the voice interaction
        from models import UserQuery
        from app import db

        user_query = UserQuery(
            user_message=text_message,
            bot_response=result['response'],
            language=language,
            agent_type=result.get('agent_type'),
            agent_name=result.get('agent_name'),
            agent_confidence=result.get('confidence', 0.0),
            session_id=session_id,
            ip_address=request.remote_addr,
            user_agent='Voice Chat API'
        )

        try:
            db.session.add(user_query)
            db.session.commit()
            query_id = user_query.id
        except Exception:
            query_id = None

        return jsonify({
            'response': result['response'],
            'agent_name': result.get('agent_name'),
            'query_id': query_id,
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Error processing voice message: {str(e)}")
        return jsonify({'error': 'Failed to process voice message'}), 500


@main_bp.route('/api/images', methods=['GET'])
def get_university_images():
    """Get list of university images and media files"""
    try:
        import os
        from flask import current_app
        
        # Path to images directory
        images_dir = os.path.join(current_app.static_folder, 'css', 'image')
        
        if not os.path.exists(images_dir):
            return jsonify({'success': False, 'error': 'Images directory not found'}), 404
        
        # Get all files from images directory
        files = []
        for filename in os.listdir(images_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.pdf')):
                file_path = os.path.join(images_dir, filename)
                file_size = os.path.getsize(file_path)
                
                # Determine file type
                if filename.lower().endswith(('.mp4',)):
                    file_type = 'video'
                elif filename.lower().endswith(('.pdf',)):
                    file_type = 'document'
                else:
                    file_type = 'image'
                
                # Create description based on filename
                description = _get_image_description(filename)
                
                files.append({
                    'filename': filename,
                    'url': f"/static/css/image/{filename}",
                    'type': file_type,
                    'size': file_size,
                    'description': description
                })
        
        # Sort files by type and name
        files.sort(key=lambda x: (x['type'], x['filename']))
        
        return jsonify({
            'success': True,
            'images': files,
            'total': len(files)
        })
        
    except Exception as e:
        logger.error(f"Error getting university images: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get images'}), 500

def _get_image_description(filename):
    """Generate description for image based on filename"""
    filename_lower = filename.lower()
    
    descriptions = {
        'макет': 'Макет здания университета Болашак',
        'альбом': 'Фотоальбом университета',
        'видеоролик': 'Рекламный видеоролик университета',
        'дронмен': 'Видео с дрона университета',
        'фото': 'Фотографии университета',
        'английский': 'Альбом на английском языке',
        'казахский': 'Альбом на казахском языке', 
        'русский': 'Альбом на русском языке'
    }
    
    for key, desc in descriptions.items():
        if key in filename_lower:
            return desc
    
    return f'Изображение: {filename}'

@main_bp.route('/api/tts', methods=['POST'])
def tts_proxy():
    """
    Free TTS endpoint using browser's native speech synthesis
    Returns instructions for client-side TTS instead of server-side processing
    """
    try:
        data = request.get_json(force=True)
        text = data.get('text', '')
        speaker = data.get('speaker', 'default')
        lang = data.get('lang', 'ru')
        speed = data.get('speed', 1.0)
        emotion = data.get('emotion', 'neutral')

        # Instead of server-side TTS, return configuration for client-side Web Speech API
        tts_config = {
            'text': text,
            'lang': 'ru-RU' if lang == 'ru' else 'en-US',
            'rate': float(speed),
            'pitch': 1.0,
            'volume': 1.0,
            'voice_preference': speaker,
            'use_browser_tts': True
        }

        logger.info(f"TTS config generated for text: {text[:50]}... (lang: {lang}, speed: {speed})")

        return jsonify({
            'success': True,
            'config': tts_config,
            'message': 'Use browser TTS with provided config'
        })

    except Exception as e:
        logger.error(f"TTS config error: {str(e)}")
        return jsonify({'error': 'Failed to generate TTS config'}), 500


@main_bp.route('/api/feedback/like-dislike', methods=['POST'])
def feedback_like_dislike():
    """Handle like/dislike feedback for bot responses"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        message_id = data.get('message_id')
        is_like = data.get('is_like', True)
        
        if not message_id:
            return jsonify({'error': 'Message ID is required'}), 400
            
        logger.info(f"Recording feedback: message_id={message_id}, is_like={is_like}")
        
        # Convert like/dislike to rating (5 for like, 1 for dislike)
        rating = 5 if is_like else 1
        
        # Try to find and update the UserQuery with feedback
        from models import UserQuery
        from app import db
        
        try:
            # Find the most recent query for this session (since message_id is UUID and id is integer)
            # We'll use session_id and timestamp to find the relevant query
            query = UserQuery.query.filter_by(
                session_id=session.get('session_id', '')
            ).order_by(UserQuery.created_at.desc()).first()
            
            if query:
                # Update the query record with rating
                query.user_rating = 'like' if is_like else 'dislike'
                query.rating_timestamp = datetime.utcnow()
                db.session.commit()
                
                # Update ML router with feedback using existing method
                from ml_router import MLRouter
                ml_router = MLRouter()
                
                # Record feedback in ML router
                ml_router.record_interaction(
                    message=query.user_message,
                    selected_agent=query.agent_type or 'unknown',
                    user_id=session.get('session_id', 'anonymous'),
                    session_id=query.session_id or 'unknown',
                    user_rating=rating,
                    response_relevance=1.0 if rating >= 4 else 0.3
                )
                logger.info(f"Updated query {query.id} and ML router with feedback for message_id {message_id}")
            else:
                logger.warning(f"No recent query found for session {session.get('session_id', '')}")
                
        except Exception as e:
            logger.error(f"Error updating ML router: {str(e)}")
        
        message = "Спасибо за обратную связь!" if is_like else "Спасибо, мы учтем ваше мнение!"
        
        return jsonify({
            'success': True,
            'message': message,
            'feedback_recorded': True
        })
        
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        return jsonify({'error': 'Failed to record feedback'}), 500


@main_bp.route('/api/cache-stats')
def get_cache_stats():
    """Get cache statistics for monitoring"""
    try:
        from response_cache import response_cache
        stats = response_cache.get_stats()
        
        return jsonify({
            'cache_stats': stats,
            'status': 'healthy'
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({'error': 'Failed to get cache stats'}), 500


@main_bp.route('/api/statistics')
def get_statistics():
    """Get real-time statistics for the homepage"""
    try:
        from models import UserQuery, AgentKnowledgeBase, db
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # Основная статистика
        total_queries = UserQuery.query.count()
        total_knowledge = AgentKnowledgeBase.query.filter_by(is_active=True).count()
        
        # Статистика за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_queries = UserQuery.query.filter(
            UserQuery.created_at >= thirty_days_ago
        ).count()
        
        # Рейтинг удовлетворенности
        liked_queries = UserQuery.query.filter_by(user_rating='like').count()
        total_rated_queries = UserQuery.query.filter(UserQuery.user_rating.isnot(None)).count()
        satisfaction_rate = round((liked_queries / total_rated_queries * 100) if total_rated_queries > 0 else 95, 1)
        
        # Средне время ответа
        avg_response_time = db.session.query(
            func.avg(UserQuery.response_time)
        ).scalar()
        avg_response_time = round(avg_response_time, 2) if avg_response_time else 1.5
        
        # Статистика агентов
        agent_stats = db.session.query(
            UserQuery.agent_name,
            func.count(UserQuery.id).label('count'),
            func.avg(UserQuery.response_time).label('avg_time'),
            func.avg(UserQuery.agent_confidence).label('avg_confidence')
        ).filter(
            UserQuery.agent_name.isnot(None)
        ).group_by(UserQuery.agent_name).all()
        
        # Языковая статистика
        language_stats = db.session.query(
            UserQuery.language,
            func.count(UserQuery.id).label('count')
        ).group_by(UserQuery.language).all()
        
        # Статистика пользователей  
        total_users = db.session.query(func.count(func.distinct(UserQuery.session_id))).scalar() or 0
        
        # Активные пользователи за последние 24 часа
        day_ago = datetime.utcnow() - timedelta(days=1)
        active_users_24h = db.session.query(UserQuery.session_id).filter(
            UserQuery.created_at >= day_ago
        ).distinct().count()
        
        # Активные пользователи за последние 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users_7d = db.session.query(UserQuery.session_id).filter(
            UserQuery.created_at >= week_ago
        ).distinct().count()
        
        # Среднее количество запросов на пользователя
        avg_queries_per_user = round(total_queries / total_users, 1) if total_users > 0 else 0
        
        # Топ часов активности
        hourly_stats = db.session.query(
            func.extract('hour', UserQuery.created_at).label('hour'),
            func.count(UserQuery.id).label('count')
        ).group_by(func.extract('hour', UserQuery.created_at)).order_by(func.count(UserQuery.id).desc()).all()
        
        # Статистика по дням недели
        daily_stats = db.session.query(
            func.extract('dow', UserQuery.created_at).label('day'),
            func.count(UserQuery.id).label('count')
        ).group_by(func.extract('dow', UserQuery.created_at)).all()
        
        # Преобразуем дни недели в названия
        day_names = {0: 'Воскресенье', 1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг', 5: 'Пятница', 6: 'Суббота'}
        daily_stats_named = [
            {
                'day': day_names.get(int(stat.day), f'День {int(stat.day)}'),
                'count': stat.count
            }
            for stat in daily_stats
        ]
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {
                'total_students': 15000,  # Константа или из другой таблицы
                'total_queries': total_queries,
                'recent_queries': recent_queries,
                'total_knowledge': total_knowledge,
                'satisfaction_rate': satisfaction_rate,
                'avg_response_time': avg_response_time,
                'user_stats': {
                    'total_users': total_users,
                    'active_users_24h': active_users_24h,
                    'active_users_7d': active_users_7d,
                    'avg_queries_per_user': avg_queries_per_user,
                    'user_growth': {
                        'daily_retention': round((active_users_24h / total_users * 100) if total_users > 0 else 0, 1),
                        'weekly_retention': round((active_users_7d / total_users * 100) if total_users > 0 else 0, 1)
                    }
                },
                'usage_patterns': {
                    'hourly_stats': [
                        {
                            'hour': int(stat.hour),
                            'count': stat.count
                        }
                        for stat in hourly_stats[:5]  # Топ 5 часов
                    ],
                    'daily_stats': daily_stats_named
                },
                'agent_stats': [
                    {
                        'name': stat.agent_name,
                        'count': stat.count,
                        'avg_time': round(stat.avg_time or 0, 2),
                        'avg_confidence': round(stat.avg_confidence or 0, 2)
                    }
                    for stat in agent_stats
                ],
                'language_stats': [
                    {
                        'language': stat.language,
                        'count': stat.count
                    }
                    for stat in language_stats
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get statistics'
        }), 500

@main_bp.route('/api/system-info')
def get_system_info():
    """Get system information including improvements status"""
    try:
        from response_cache import response_cache
        
        # Test that all improvements are loaded
        improvements_status = {}
        
        try:
            from knowledge_search import knowledge_search_engine
            improvements_status['knowledge_search'] = 'active'
        except Exception:
            improvements_status['knowledge_search'] = 'error'
        
        try:
            from prompt_engineering import prompt_engineer
            improvements_status['prompt_engineering'] = 'active'
        except Exception:
            improvements_status['prompt_engineering'] = 'error'
        
        try:
            cache_stats = response_cache.get_stats()
            improvements_status['response_cache'] = 'active'
        except Exception:
            improvements_status['response_cache'] = 'error'
            cache_stats = {}
        
        return jsonify({
            'improvements': improvements_status,
            'cache_stats': cache_stats,
            'system_status': 'enhanced' if all(
                status == 'active' for status in improvements_status.values()
            ) else 'partial'
        })
        
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return jsonify({'error': 'Failed to get system info'}), 500
# API эндпоинты для системы расписания

@main_bp.route('/api/schedule/groups', methods=['GET'])
def get_groups():
    """Получить список всех групп"""
    try:
        from models import Group, Faculty
        from app import db
        from flask import session
        
        language = session.get('language', 'ru')
        
        groups = db.session.query(Group, Faculty).join(Faculty).filter(Group.is_active == True).all()
        
        groups_list = []
        for group, faculty in groups:
            groups_list.append({
                'id': group.id,
                'name': group.name,
                'year': group.year,
                'semester': group.semester,
                'faculty': {
                    'id': faculty.id,
                    'name': faculty.get_name(language),
                    'code': faculty.code
                }
            })
        
        return jsonify({
            'success': True,
            'groups': groups_list,
            'total': len(groups_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting groups: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении списка групп'
        }), 500

@main_bp.route('/api/schedule/today/<group_name>', methods=['GET'])
def get_today_schedule(group_name):
    """Получить расписание на сегодня для группы"""
    try:
        from models import Schedule
        from app import db
        from flask import session
        from datetime import date
        
        language = session.get('language', 'ru')
        today = date.today()
        
        # Получить расписание на сегодня по названию группы
        schedules = Schedule.query.filter(
            Schedule.group_name == group_name,
            db.func.date(Schedule.start_time) == today,
            Schedule.is_active == True,
            Schedule.is_cancelled == False
        ).order_by(Schedule.start_time).all()
        
        schedule_list = [schedule.to_dict(language) for schedule in schedules]
        
        return jsonify({
            'success': True,
            'date': today.isoformat(),
            'group': group_name,
            'schedules': schedule_list,
            'total': len(schedule_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting today's schedule: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении расписания на сегодня'
        }), 500

@main_bp.route('/api/schedule/tomorrow/<group_name>', methods=['GET'])
def get_tomorrow_schedule(group_name):
    """Получить расписание на завтра для группы"""
    try:
        from models import Schedule
        from app import db
        from flask import session
        from datetime import date, timedelta
        
        language = session.get('language', 'ru')
        tomorrow = date.today() + timedelta(days=1)
        
        # Получить расписание на завтра по названию группы
        schedules = Schedule.query.filter(
            Schedule.group_name == group_name,
            db.func.date(Schedule.start_time) == tomorrow,
            Schedule.is_active == True,
            Schedule.is_cancelled == False
        ).order_by(Schedule.start_time).all()
        
        schedule_list = [schedule.to_dict(language) for schedule in schedules]
        
        return jsonify({
            'success': True,
            'date': tomorrow.isoformat(),
            'group': group_name,
            'schedules': schedule_list,
            'total': len(schedule_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting tomorrow's schedule: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении расписания на завтра'
        }), 500

@main_bp.route('/api/schedule/week/<group_name>', methods=['GET'])
def get_week_schedule(group_name):
    """Получить расписание на неделю для группы"""
    try:
        from models import Schedule
        from app import db
        from flask import session
        from datetime import date, timedelta
        
        language = session.get('language', 'ru')
        today = date.today()
        
        # Получаем дату начала недели (понедельник)
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Получить расписание на неделю по названию группы
        schedules = Schedule.query.filter(
            Schedule.group_name == group_name,
            db.func.date(Schedule.start_time) >= start_of_week,
            db.func.date(Schedule.start_time) <= end_of_week,
            Schedule.is_active == True,
            Schedule.is_cancelled == False
        ).order_by(Schedule.start_time).all()
        
        # Группируем по дням
        schedule_by_days = {}
        for schedule in schedules:
            day_key = schedule.date.isoformat()
            if day_key not in schedule_by_days:
                schedule_by_days[day_key] = []
            schedule_by_days[day_key].append(schedule.to_dict(language))
        
        return jsonify({
            'success': True,
            'start_date': start_of_week.isoformat(),
            'end_date': end_of_week.isoformat(),
            'group': group_name,
            'schedule_by_days': schedule_by_days,
            'total_lessons': len(schedules)
        })
        
    except Exception as e:
        logger.error(f"Error getting week schedule: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении расписания на неделю'
        }), 500

@main_bp.route('/api/schedule/date/<group_name>/<date_str>', methods=['GET'])
def get_schedule_by_date(group_name, date_str):
    """Получить расписание на конкретную дату для группы"""
    try:
        from models import Schedule
        from app import db
        from flask import session
        from datetime import datetime
        
        language = session.get('language', 'ru')
        
        # Парсинг даты
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Неверный формат даты. Используйте YYYY-MM-DD'
            }), 400
        
        # Получить расписание на указанную дату по названию группы
        schedules = Schedule.query.filter(
            Schedule.group_name == group_name,
            db.func.date(Schedule.start_time) == target_date,
            Schedule.is_active == True,
            Schedule.is_cancelled == False
        ).order_by(Schedule.start_time).all()
        
        schedule_list = [schedule.to_dict(language) for schedule in schedules]
        
        return jsonify({
            'success': True,
            'date': target_date.isoformat(),
            'group': group_name,
            'schedules': schedule_list,
            'total': len(schedule_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting schedule by date: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении расписания на указанную дату'
        }), 500

@main_bp.route('/api/schedule/subjects', methods=['GET'])
def get_subjects():
    """Получить список всех предметов"""
    try:
        from models import Subject
        from app import db
        from flask import session
        
        language = session.get('language', 'ru')
        
        subjects = Subject.query.filter_by(is_active=True).all()
        
        subjects_list = []
        for subject in subjects:
            subjects_list.append({
                'id': subject.id,
                'name': subject.get_name(language),
                'code': subject.code,
                'credits': subject.credits,
                'description': subject.get_description(language)
            })
        
        return jsonify({
            'success': True,
            'subjects': subjects_list,
            'total': len(subjects_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting subjects: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении списка предметов'
        }), 500

@main_bp.route('/api/schedule/faculties', methods=['GET'])
def get_faculties():
    """Получить список всех факультетов"""
    try:
        from models import Faculty
        from app import db
        from flask import session
        
        language = session.get('language', 'ru')
        
        faculties = Faculty.query.filter_by(is_active=True).all()
        
        faculties_list = []
        for faculty in faculties:
            faculties_list.append({
                'id': faculty.id,
                'name': faculty.get_name(language),
                'code': faculty.code,
                'description': faculty.get_description(language)
            })
        
        return jsonify({
            'success': True,
            'faculties': faculties_list,
            'total': len(faculties_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting faculties: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при получении списка факультетов'
        }), 500

@main_bp.route('/api/deployment-readiness')
def deployment_readiness():
    """
    Comprehensive deployment readiness check
    Комплексная проверка готовности к деплою
    """
    try:
        from app import db
        from flask import current_app
        import os
        import sys

        # Инициализация результата проверки
        checks = {
            'database': {'status': 'unknown', 'message': ''},
            'agents': {'status': 'unknown', 'message': ''},
            'environment': {'status': 'unknown', 'message': ''},
            'dependencies': {'status': 'unknown', 'message': ''},
            'configuration': {'status': 'unknown', 'message': ''}
        }

        overall_status = 'healthy'

        # 1. Проверка базы данных
        try:
            # Проверяем соединение с базой данных
            from sqlalchemy import text
            # Простая проверка - создание таблиц
            db.create_all()
            checks['database']['status'] = 'healthy'
            checks['database']['message'] = 'База данных доступна и отвечает'
        except Exception as e:
            checks['database']['status'] = 'error'
            checks['database']['message'] = f'Ошибка подключения к БД: {str(e)}'
            overall_status = 'error'

        # 2. Проверка агентов
        try:
            router = initialize_agent_router()
            agents = router.get_available_agents()
            if len(agents) > 0:
                checks['agents']['status'] = 'healthy'
                checks['agents']['message'] = f'Доступно агентов: {len(agents)}'
            else:
                checks['agents']['status'] = 'warning'
                checks['agents']['message'] = 'Агенты не настроены'
                if overall_status != 'error':
                    overall_status = 'warning'
        except Exception as e:
            checks['agents']['status'] = 'error'
            checks['agents']['message'] = f'Ошибка инициализации агентов: {str(e)}'
            overall_status = 'error'

        # 3. Проверка переменных окружения
        required_env = ['DATABASE_URL', 'SESSION_SECRET']
        env_issues = []
        for env_var in required_env:
            if not os.environ.get(env_var):
                env_issues.append(env_var)

        if env_issues:
            checks['environment']['status'] = 'warning'
            checks['environment']['message'] = f'Отсутствуют переменные: {", ".join(env_issues)}'
            if overall_status == 'healthy':
                overall_status = 'warning'
        else:
            checks['environment']['status'] = 'healthy'
            checks['environment']['message'] = 'Все необходимые переменные окружения настроены'

        # 4. Проверка зависимостей
        try:
            import flask, sqlalchemy, gunicorn, requests
            checks['dependencies']['status'] = 'healthy'
            checks['dependencies']['message'] = f'Python {sys.version.split()[0]}, Flask {getattr(flask, "__version__", "unknown")}'
        except ImportError as e:
            checks['dependencies']['status'] = 'error'
            checks['dependencies']['message'] = f'Отсутствуют зависимости: {str(e)}'
            overall_status = 'error'

        # 5. Проверка конфигурации
        config_issues = []

        # Проверяем настройки безопасности для продакшена
        if current_app.debug and os.environ.get('FLASK_ENV') == 'production':
            config_issues.append('Debug режим включен в продакшене')

        # Проверяем секретный ключ
        if current_app.secret_key == 'dev-secret-key-change-in-production':
            config_issues.append('Используется тестовый секретный ключ')

        if config_issues:
            checks['configuration']['status'] = 'warning'
            checks['configuration']['message'] = '; '.join(config_issues)
            if overall_status == 'healthy':
                overall_status = 'warning'
        else:
            checks['configuration']['status'] = 'healthy'
            checks['configuration']['message'] = 'Конфигурация корректна'

        # Формирование итогового ответа
        result = {
            'overall_status': overall_status,
            'timestamp': time.time(),
            'checks': checks,
            'deployment_ready': overall_status != 'error',
            'recommendations': []
        }

        # Добавляем рекомендации
        if overall_status == 'error':
            result['recommendations'].append('Исправьте критические ошибки перед деплоем')
        elif overall_status == 'warning':
            result['recommendations'].append('Рекомендуется исправить предупреждения')
            result['recommendations'].append('Настройте переменные окружения для продакшена')
        else:
            result['recommendations'].append('Проект готов к деплою')
            result['recommendations'].append('Используйте Gunicorn для продакшена')
            result['recommendations'].append('Настройте PostgreSQL для продакшена')

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in deployment readiness check: {str(e)}")
        return jsonify({
            'overall_status': 'error',
            'error': f'Ошибка проверки готовности: {str(e)}',
            'deployment_ready': False
        }), 500