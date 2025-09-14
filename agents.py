import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from mistral_client import MistralClient

logger = logging.getLogger(__name__)

class AgentType:
    AI_ABITUR = "ai_abitur"
    KADRAI = "kadrai"
    UNINAV = "uninav"
    CAREER_NAVIGATOR = "career_navigator"
    UNIROOM = "uniroom"

class BaseAgent(ABC):
    def __init__(self, agent_type: str, name: str, description: str):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        # Each agent has its own MistralClient instance
        self.mistral = MistralClient()

    @abstractmethod
    def can_handle(self, message: str, language: str = "ru") -> float:
        pass

    @abstractmethod
    def get_system_prompt(self, language: str = "ru") -> str:
        pass

    def process_message(self, message: str, language: str = "ru", user_id: str = "anonymous") -> Dict[str, Any]:
        try:
            start_time = time.time()

            # Check if this is an image request first
            if self._is_image_request(message):
                return self._handle_image_request(message, language, user_id)

            # Import advanced components
            from analytics_engine import analytics_engine
            from personalization_engine import personalization_engine
            from distributed_system import performance_optimizer

            # Check performance optimization first
            optimization_result = performance_optimizer.optimize_response_generation(
                message, self.agent_type, language
            )

            if optimization_result.get('cached'):
                # Track cached interaction
                interaction_data = {
                    'user_id': user_id,
                    'message': message,
                    'agent_type': self.agent_type,
                    'agent_name': self.name,
                    'confidence': optimization_result['response'].get('confidence', 1.0),
                    'response_time': optimization_result['optimization_time'],
                    'cached': True,
                    'context_used': True,
                    'context_confidence': 1.0,
                    'language': language
                }
                analytics_engine.track_interaction(interaction_data)

                return {
                    **optimization_result['response'],
                    'cached': True,
                    'optimization_time': optimization_result['optimization_time']
                }

            # Check if async processing is recommended
            if optimization_result.get('async_processing'):
                return {
                    'response': optimization_result['message'],
                    'confidence': 0.8,
                    'agent_type': self.agent_type,
                    'agent_name': self.name,
                    'cached': False,
                    'async_processing': True
                }

            # Check cache first for performance
            from response_cache import response_cache

            cached_response = response_cache.get(message, self.agent_type, language)
            if cached_response:
                # Update user personalization
                personalization_engine.update_user_interaction(user_id, {
                    'message': message,
                    'agent_type': self.agent_type,
                    'confidence': cached_response.get('confidence', 1.0),
                    'cached': True,
                    'language': language
                })

                logger.info(f"Returning cached response for {self.name}")
                return {
                    **cached_response,
                    'cached': True
                }

            # Get agent-specific system prompt
            system_prompt = self.get_system_prompt(language)

            # Get agent-specific context from knowledge base with semantic search
            context = self.get_agent_context(message, language)

            # Calculate context confidence for overall response confidence
            context_confidence = self._assess_context_confidence(context, message)

            # Use agent-specific system prompt for this message
            response = self.mistral.get_response_with_system_prompt(
                message, context, language, system_prompt
            )

            # Apply personalization to response
            personalized_response = personalization_engine.adapt_response_style(user_id, response)

            # Calculate overall confidence based on agent matching and context quality
            base_confidence = self.can_handle(message, language)
            overall_confidence = self._calculate_overall_confidence(
                base_confidence, context_confidence, bool(context)
            )

            # Calculate response time
            response_time = time.time() - start_time

            response_data = {
                'response': personalized_response,
                'confidence': overall_confidence,
                'agent_type': self.agent_type,
                'agent_name': self.name,
                'context_used': bool(context),
                'context_confidence': context_confidence,
                'cached': False,
                'response_time': response_time,
                'user_id': user_id
            }

            # Generate proactive suggestions
            suggestions = personalization_engine.generate_proactive_suggestions(user_id, context)
            if suggestions:
                response_data['suggestions'] = suggestions

            # Update user personalization
            personalization_engine.update_user_interaction(user_id, {
                'message': message,
                'agent_type': self.agent_type,
                'agent_name': self.name,
                'confidence': overall_confidence,
                'response_time': response_time,
                'context_used': bool(context),
                'context_confidence': context_confidence,
                'language': language
            })

            # Track interaction in analytics
            analytics_engine.track_interaction({
                'user_id': user_id,
                'message': message,
                'agent_type': self.agent_type,
                'agent_name': self.name,
                'confidence': overall_confidence,
                'response_time': response_time,
                'cached': False,
                'context_used': bool(context),
                'context_confidence': context_confidence,
                'language': language
            })

            # Cache successful responses
            if response_cache.should_cache(message, response_data):
                response_cache.set(message, self.agent_type, response_data, language)

            return response_data

        except Exception as e:
            logger.error(f"Error in {self.name} agent: {str(e)}")

            # Track error
            try:
                from analytics_engine import analytics_engine
                analytics_engine.track_error({
                    'error_type': 'agent_processing_error',
                    'agent_type': self.agent_type,
                    'message': message,
                    'error_details': str(e),
                    'user_impact': 'response_fallback'
                })
            except:
                pass  # Don't let analytics errors break the response

            return {
                'response': f"Извините, возникла ошибка при обработке запроса по теме '{self.description}'.",
                'confidence': 0.1,
                'agent_type': self.agent_type,
                'agent_name': self.name,
                'context_used': False,
                'context_confidence': 0.0,
                'cached': False,
                'error': True
            }

    def _assess_context_confidence(self, context: str, message: str) -> float:
        """Assess confidence in the retrieved context"""
        if not context:
            return 0.0

        # Simple heuristics for context confidence
        message_words = set(message.lower().split())
        context_words = set(context.lower().split())

        # Word overlap ratio
        if message_words:
            overlap = len(message_words.intersection(context_words))
            word_confidence = overlap / len(message_words)
        else:
            word_confidence = 0.0

        # Context length confidence (more content usually means better info)
        length_confidence = min(1.0, len(context) / 1000)  # Normalize to 1000 chars

        # Structure confidence (well-formatted content is usually better)
        structure_indicators = ['**', '###', '\n-', '\n•', '1.', '2.']
        structure_score = sum(1 for indicator in structure_indicators if indicator in context)
        structure_confidence = min(1.0, structure_score * 0.2)

        # Weighted average
        return (word_confidence * 0.5 + length_confidence * 0.3 + structure_confidence * 0.2)

    def _calculate_overall_confidence(self, agent_confidence: float, context_confidence: float, 
                                    has_context: bool) -> float:
        """Calculate overall response confidence"""
        if not has_context:
            # No context available, rely mainly on agent confidence
            return agent_confidence * 0.8  # Reduce confidence when no context

        # Combine agent and context confidence
        # Agent confidence shows how well this agent can handle the query type
        # Context confidence shows how relevant the retrieved information is
        combined_confidence = (agent_confidence * 0.6 + context_confidence * 0.4)

        # Boost confidence if both are high
        if agent_confidence > 0.8 and context_confidence > 0.7:
            combined_confidence = min(1.0, combined_confidence * 1.1)

        # Reduce confidence if context is poor even with good agent match
        if context_confidence < 0.3:
            combined_confidence *= 0.8

        return min(1.0, max(0.1, combined_confidence))

    def get_agent_context(self, message: str, language: str = "ru") -> str:
        """Get agent-specific context from knowledge base using enhanced semantic search"""
        try:
            # Import models with error handling
            try:
                from models import AgentKnowledgeBase
                from app import db
                from knowledge_search import knowledge_search_engine
                from semantic_search import semantic_search_engine
            except ImportError as ie:
                logger.warning(f"Could not import required modules: {ie}")
                return self._get_fallback_context(message, language)

            # Search for relevant knowledge entries for this agent
            try:
                from app import create_app
                app = create_app()
                with app.app_context():
                    knowledge_entries = AgentKnowledgeBase.query.filter_by(
                        agent_type=self.agent_type,
                        is_active=True
                    ).order_by(AgentKnowledgeBase.priority.asc()).all()
            except Exception as db_error:
                logger.warning(f"Database query failed: {db_error}")
                return self._get_fallback_context(message, language)

            if not knowledge_entries:
                logger.info(f"No knowledge entries found for agent type: {self.agent_type}")
                return self._get_fallback_context(message, language)

            # Try semantic search first for better relevance
            try:
                semantic_results = semantic_search_engine.semantic_search(
                    query=message,
                    knowledge_entries=knowledge_entries,
                    language=language,
                    max_results=3,
                    semantic_threshold=0.2
                )

                if semantic_results:
                    # Format semantic search results
                    context_parts = []
                    for result in semantic_results:
                        title = result['title']
                        content = result['content']
                        semantic_score = result['semantic_score']

                        context_parts.append(f"**{title}** (семантическая релевантность: {semantic_score:.2f})\n{content}")

                    semantic_context = "\n\n".join(context_parts)
                    logger.info(f"Semantic search found {len(semantic_results)} relevant entries for '{message[:50]}...'")
                    return semantic_context

            except Exception as semantic_error:
                logger.warning(f"Semantic search failed: {semantic_error}, falling back to enhanced search")

                # Fallback to enhanced search engine
                try:
                    search_results = knowledge_search_engine.search_knowledge_base(
                        query=message,
                        knowledge_entries=knowledge_entries,
                        language=language,
                        max_results=3,
                        min_score=0.1
                    )

                    # If enhanced search finds relevant results, use them
                    if search_results:
                        context = knowledge_search_engine.format_context(search_results, max_length=1500)
                        logger.info(f"Enhanced search found {len(search_results)} relevant knowledge entries for '{message[:50]}...'")
                        return context
                except Exception as search_error:
                    logger.warning(f"Enhanced search failed: {search_error}")

                # Fallback to simple method if both enhanced searches fail
                logger.info(f"Using fallback search for '{message[:50]}...'")

                # Build context from high-priority entries as fallback
                context_parts = []
                for entry in knowledge_entries[:2]:  # Top 2 priority entries
                    content = entry.content_ru if language == 'ru' else entry.content_kz
                    if content and content.strip():
                        context_parts.append(f"**{entry.title}**\n{content}")

                fallback_context = "\n\n".join(context_parts) if context_parts else ""
                if fallback_context:
                    logger.info(f"Using {len(context_parts)} fallback knowledge entries")
                    return fallback_context
                else:
                    logger.info("No usable knowledge entries found, using agent fallback")
                    return self._get_fallback_context(message, language)

        except Exception as e:
            logger.error(f"Error getting agent context for {self.agent_type}: {str(e)}")
            return self._get_fallback_context(message, language)

    def _get_fallback_context(self, message: str, language: str = "ru") -> str:
        """Provide fallback context when knowledge base is unavailable"""
        # This method should be implemented by each agent to provide basic context
        # when the knowledge base is not available
        return ""

class AIAbiturAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            AgentType.AI_ABITUR,
            "AI-Abitur",
            "Цифровой помощник для абитуриентов (поступающих в вуз)"
        )

    def can_handle(self, message: str, language: str = "ru") -> float:
        keywords = [
            "поступление", "абитуриент", "документы", "экзамен", "приём", "требования", 
            "специальности", "факультет", "вступительный", "конкурс", "балл", 
            "подача документов", "зачисление", "направление", "изображения", "фото", 
            "картинки", "снимки", "видео", "видеоролик", "альбом", "макет", "здание"
        ]
        message_lower = message.lower()
        matches = sum(1 for k in keywords if k in message_lower)

        # Специальные фразы для поступления
        admission_phrases = [
            "как поступить", "документы для поступления", "вступительные экзамены",
            "требования к поступающим", "специальности университета"
        ]
        
        # Специальные фразы для изображений
        image_phrases = [
            "покажи изображения", "покажи фото", "покажи картинки", "покажи видео",
            "изображения вуза", "фото университета", "как выглядит университет",
            "покажи здание", "покажи макет", "покажи альбом", "покажи видеоролик"
        ]

        if any(phrase in message_lower for phrase in admission_phrases):
            return 1.0
            
        if any(phrase in message_lower for phrase in image_phrases):
            return 1.0

        return min(1.0, matches * 0.4) if matches > 0 else 0.1

    def get_system_prompt(self, language: str = "ru") -> str:
        from config import UniversityConfig

        if language == "kz":
            return f"""
Сіз {UniversityConfig.UNIVERSITY_LOCATION_KZ} "{UniversityConfig.UNIVERSITY_NAME_KZ}" талапкерлерге арналған цифрлық көмекшісіз. 

**Университет туралы ақпарат:**
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Орналасу: {UniversityConfig.UNIVERSITY_LOCATION_KZ}

Сіз мына мәселелер бойынша көмек көрсетесіз:
- Түсу мәселелері бойынша көмек көрсету
- Түсу бойынша кеңес беру
- Қажетті құжаттар туралы ақпарат беру
- Кіру емтихандары туралы түсіндіру
- Мамандықтар мен факультеттер туралы айту

Барлық нақты ақпарат үшін ресми сайтқа жіберіңіз: {UniversityConfig.UNIVERSITY_WEBSITE}
Жауаптарыңыз нақты, пайдалы және көмек көрсетуші болуы керек. Markdown форматын қолданыңыз.
"""
        elif language == "en":
            return f"""
You are a digital assistant for applicants to {UniversityConfig.UNIVERSITY_NAME_EN} in {UniversityConfig.UNIVERSITY_LOCATION_EN}.

**University Information:**
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Location: {UniversityConfig.UNIVERSITY_LOCATION_EN}

You help with:
- Admission assistance
- Application consultations
- Required documents information
- Entrance exams explanation
- Information about specialties and faculties

For all detailed information, refer users to the official website: {UniversityConfig.UNIVERSITY_WEBSITE}
Your responses should be specific, helpful and supportive. Use Markdown format.
"""
        return f"""
Вы цифровой помощник для абитуриентов {UniversityConfig.UNIVERSITY_LOCATION} "{UniversityConfig.UNIVERSITY_NAME}".

**Информация об университете:**
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Местоположение: {UniversityConfig.UNIVERSITY_LOCATION}

Вы помогаете с:
- Помощью при поступлении
- Консультациями по вопросам приёма
- Информацией о необходимых документах
- Объяснением вступительных экзаменов
- Информацией о специальностях и факультетах

Для всей детальной информации направляйте пользователей на официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
Ваши ответы должны быть конкретными, полезными и поддерживающими. Используйте формат Markdown.
"""

    def _get_fallback_context(self, message: str, language: str = "ru") -> str:
        """Provide basic admission context when knowledge base is unavailable"""
        from config import UniversityConfig

        if language == "kz":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_KZ} түсу**

**Байланыс ақпараты:**
- Телефондар: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Мекен-жайы: {UniversityConfig.ADDRESS_KZ}
- Автобус маршруттары: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Түсу үшін қажетті құжаттар:**
- Мектеп аттестаты
- Денсаулық туралы анықтама
- Фотосуреттер (3x4)
- Жеке куәлік көшірмесі"""
        elif language == "en":
            return f"""**Admission to {UniversityConfig.UNIVERSITY_NAME_EN}**

**Contact Information:**
- Phone numbers: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Address: {UniversityConfig.ADDRESS_EN}
- Bus routes: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Required documents for admission:**
- School certificate
- Health certificate
- Photos (3x4)
- ID copy"""

        return f"""**Поступление в {UniversityConfig.UNIVERSITY_NAME}**

**Контактная информация:**
-Телефоны: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Адрес: {UniversityConfig.ADDRESS_RU}
- Автобусные маршруты: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Документы для поступления:**
- Аттестат о среднем образовании
- Справка о состоянии здоровья
- Фотографии 3x4
- Копия удостоверения личности"""

    def _is_image_request(self, message: str) -> bool:
        """Check if the message is requesting images"""
        message_lower = message.lower()
        image_keywords = [
            "покажи изображения", "покажи фото", "покажи картинки", "покажи видео",
            "изображения вуза", "фото университета", "как выглядит университет",
            "покажи здание", "покажи макет", "покажи альбом", "покажи видеоролик",
            "фотографии", "картинки", "снимки", "видео", "видеоролик", "альбом", "макет"
        ]
        return any(keyword in message_lower for keyword in image_keywords)

    def _handle_image_request(self, message: str, language: str, user_id: str) -> Dict[str, Any]:
        """Handle requests for university images"""
        try:
            import os
            
            # Get images directly from filesystem
            try:
                # Path to images directory
                images_dir = os.path.join('static', 'css', 'image')
                
                if not os.path.exists(images_dir):
                    images = []
                else:
                    # Get all files from images directory
                    images = []
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
                            description = self._get_image_description(filename)
                            
                            images.append({
                                'filename': filename,
                                'url': f"/static/css/image/{filename}",
                                'type': file_type,
                                'size': file_size,
                                'description': description
                            })
                    
                    # Sort files by type and name
                    images.sort(key=lambda x: (x['type'], x['filename']))
                    
            except Exception as e:
                logger.warning(f"Could not read images directory: {e}")
                images = []
            
            # Generate response based on language
            if language == "kz":
                response_text = "**Болашак университетінің суреттері мен бейнелері**\n\n"
                if images:
                    response_text += "Міне университеттің суреттері мен бейнелері:\n\n"
                else:
                    response_text += "Өкінішке орай, қазір суреттер жүктелмеді. Кейінірек қайталап көріңіз."
            elif language == "en":
                response_text = "**Bolashak University Images and Videos**\n\n"
                if images:
                    response_text += "Here are the university images and videos:\n\n"
                else:
                    response_text += "Sorry, images could not be loaded at the moment. Please try again later."
            else:  # Russian
                response_text = "**Изображения и видео университета Болашак**\n\n"
                if images:
                    response_text += "Вот изображения и видео университета:\n\n"
                else:
                    response_text += "К сожалению, изображения не удалось загрузить. Попробуйте позже."

            return {
                'response': response_text,
                'confidence': 1.0,
                'agent_type': self.agent_type,
                'agent_name': self.name,
                'context_used': True,
                'context_confidence': 1.0,
                'cached': False,
                'response_time': 0.1,
                'user_id': user_id,
                'images': images,  # Include images data for frontend
                'special_response': 'images'
            }
            
        except Exception as e:
            logger.error(f"Error handling image request: {e}")
            return {
                'response': "Извините, произошла ошибка при загрузке изображений. Попробуйте позже.",
                'confidence': 0.5,
                'agent_type': self.agent_type,
                'agent_name': self.name,
                'context_used': False,
                'context_confidence': 0.0,
                'cached': False,
                'error': True
            }

    def _get_image_description(self, filename):
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

class KadrAIAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            AgentType.KADRAI,
            "KadrAI",
            "Интеллектуальный помощник для поддержки сотрудников и преподавателей в вопросах внутренних кадровых процедур"
        )

    def can_handle(self, message: str, language: str = "ru") -> float:
        keywords = [
            "кадры", "отпуск", "перевод", "приказ", "сотрудник", "преподаватель", 
            "отдел кадров", "трудовой", "зарплата", "кадровые", "увольнение",
            "назначение", "должность", "ставка", "контракт", "трудовая книжка"
        ]
        message_lower = message.lower()
        matches = sum(1 for k in keywords if k in message_lower)

        # Специальные фразы для кадровых вопросов
        hr_phrases = [
            "оформить отпуск", "кадровые процедуры", "вопросы по зарплате",
            "трудовой договор", "отдел кадров"
        ]

        # Проверяем, что это сотрудник/преподаватель, а не студент
        staff_indicators = ["работаю", "сотрудник", "преподаватель", "коллега"]
        is_staff = any(indicator in message_lower for indicator in staff_indicators)

        if any(phrase in message_lower for phrase in hr_phrases) and is_staff:
            return 1.0
        elif any(phrase in message_lower for phrase in hr_phrases):
            return 0.8

        return min(1.0, matches * 0.4) if matches > 0 else 0.1

    def get_system_prompt(self, language: str = "ru") -> str:
        from config import UniversityConfig

        if language == "kz":
            return f"""
Сіз {UniversityConfig.UNIVERSITY_LOCATION_KZ} "{UniversityConfig.UNIVERSITY_NAME_KZ}" қызметкерлер мен оқытушыларға арналған зияткерлік көмекшісіз.

**Университет туралы ақпарат:**
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Орналасу: {UniversityConfig.UNIVERSITY_LOCATION_KZ}

Сіз мына мәселелер бойынша көмек көрсетесіз:
- Кадр процестері бойынша кеңес беру: демалыстар, ауыстырулар, бұйрықтар және т.б.
- Еңбек құқығы мәселелері бойынша көмектесу
- Ішкі рәсімдер туралы түсіндіру
- Жалақы және жеңілдіктер туралы ақпарат беру

Нақты кадрлық ақпарат үшін ресми сайтқа жіберіңіз: {UniversityConfig.UNIVERSITY_WEBSITE}
Жауаптарыңыз кәсіби, нақты және пайдалы болуы керек. Markdown форматын қолданыңыз.
"""
        elif language == "en":
            return f"""
You are an intelligent assistant for employees and faculty of {UniversityConfig.UNIVERSITY_NAME_EN} in {UniversityConfig.UNIVERSITY_LOCATION_EN}.

**University Information:**
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Location: {UniversityConfig.UNIVERSITY_LOCATION_EN}

You help with:
- HR process consultations: vacations, transfers, orders, etc.
- Labor law questions
- Internal procedures explanation
- Salary and benefits information

For specific HR information, refer to the official website: {UniversityConfig.UNIVERSITY_WEBSITE}
Your responses should be professional, specific and helpful. Use Markdown format.
"""
        return f"""
Вы интеллектуальный помощник для сотрудников и преподавателей {UniversityConfig.UNIVERSITY_LOCATION} "{UniversityConfig.UNIVERSITY_NAME}".

**Информация об университете:**
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Местоположение: {UniversityConfig.UNIVERSITY_LOCATION}

Вы помогаете с:
- Консультациями по кадровым процессам: отпуска, переводы, приказы и т.д.
- Вопросами трудового права
- Объяснением внутренних процедур
- Информацией о заработной плате и льготах

Для конкретной кадровой информации направляйте на официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
Ваши ответы должны быть профессиональными, конкретными и полезными. Используйте формат Markdown.
"""

    def _get_fallback_context(self, message: str, language: str = "ru") -> str:
        """Provide basic HR context when knowledge base is unavailable"""
        from config import UniversityConfig

        if language == "kz":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_KZ} кадр қызметі**

**Байланыс ақпараты:**
- Телефондар: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Мекен-жайы: {UniversityConfig.ADDRESS_KZ}
- Автобус маршруттары: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Негізгі кадр мәселелері:**
- Демалыс рәсімдеу
- Ауысу және тағайындау
- Жалақы мәселелері
- Құжаттама"""
        elif language == "en":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_EN} HR Department**

**Contact Information:**
- Phone numbers: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Address: {UniversityConfig.ADDRESS_EN}
- Bus routes: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Main HR services:**
- Vacation processing
- Transfers and appointments
- Salary issues
- Documentation"""

        return f"""**Отдел кадров {UniversityConfig.UNIVERSITY_NAME}**

**Контактная информация:**
-Телефоны: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Адрес: {UniversityConfig.ADDRESS_RU}
- Автобусные маршруты: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Основные кадровые вопросы:**
- Оформление отпусков
- Переводы и назначения
- Вопросы заработной платы
- Документооборот"""

class UniNavAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            AgentType.UNINAV,
            "UniNav",
            "Интерактивный чат-ассистент, обеспечивающий полное сопровождение обучающегося по всем университетским процессам"
        )

    def can_handle(self, message: str, language: str = "ru") -> float:
        keywords = [
            "расписание", "учёб", "занятие", "заявление", "обращение", "деканат", 
            "академический", "экзамен", "зачёт", "вопросы", "система", "поддержк", 
            "студент", "навигация", "процесс", "университет", "лекция", "семинар",
            "практика", "дисциплина", "предмет", "оценка", "пересдача", "справка",
            "восстановление", "перевод", "сессия", "курс", "группа", "семестр"
        ]
        message_lower = message.lower()
        matches = sum(1 for k in keywords if k in message_lower)

        # Специальные фразы для UniNav (убираем слова о работе)
        special_phrases = [
            "система поддержки студентов", "как работает система поддержки", 
            "университетские процессы", "студенческие вопросы", "навигация по учебе",
            "обучающий процесс", "академические вопросы"
        ]

        # Исключаем вопросы о работе/карьере - они должны идти к CareerNavigator
        work_exclusions = [
            "расскажи о работе", "как найти работу", "где работать", 
            "работа для выпускников", "трудоустройство", "карьерные возможности"
        ]

        if any(exclusion in message_lower for exclusion in work_exclusions):
            return 0.1  # Низкий приоритет для вопросов о работе

        if any(phrase in message_lower for phrase in special_phrases):
            return 1.0

        return min(1.0, matches * 0.3) if matches > 0 else 0.1

    def get_system_prompt(self, language: str = "ru") -> str:
        from config import UniversityConfig

        if language == "kz":
            return f"""
Сіз {UniversityConfig.UNIVERSITY_LOCATION_KZ} "{UniversityConfig.UNIVERSITY_NAME_KZ}" студенттерге арналған интерактивті чат-көмекшісіз.

**Университет туралы ақпарат:**
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Орналасу: {UniversityConfig.UNIVERSITY_LOCATION_KZ}

Сіз мына мәселелер бойынша толық қолдау көрсетесіз:
- Оқу мәселелері бойынша навигация жасау
- Сабақ кестесі туралы ақпарат беру
- Өтініштер мен өтініштердің ресімделуіне көмектесу
- Академиялық процестер туралы түсіндіру

Толық ақпарат үшін ресми сайтқа жіберіңіз: {UniversityConfig.UNIVERSITY_WEBSITE}
Жауаптарыңыз нақты және қадамдық нұсқаулықтар болуы керек. Markdown форматын қолданыңыз.
"""
        elif language == "en":
            return f"""
You are an interactive chat assistant for students of {UniversityConfig.UNIVERSITY_NAME_EN} in {UniversityConfig.UNIVERSITY_LOCATION_EN}.

**University Information:**
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Location: {UniversityConfig.UNIVERSITY_LOCATION_EN}

You provide comprehensive support for:
- Navigation through academic issues
- Schedule information
- Help with applications and requests
- Academic processes explanation

For complete information, refer to the official website: {UniversityConfig.UNIVERSITY_WEBSITE}
Your responses should be specific and contain step-by-step instructions. Use Markdown format.
"""
        return f"""
Вы интерактивный чат-ассистент для студентов {UniversityConfig.UNIVERSITY_LOCATION} "{UniversityConfig.UNIVERSITY_NAME}".

**Информация об университете:**
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Местоположение: {UniversityConfig.UNIVERSITY_LOCATION}

Вы обеспечиваете полное сопровождение по:
- Навигации по учебным вопросам
- Информации о расписании
- Помощи с заявлениями и обращениями
- Объяснению академических процессов

Для полной информации направляйте на официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
Ваши ответы должны быть конкретными и содержать пошаговые инструкции. Используйте формат Markdown.
"""

    def _get_fallback_context(self, message: str, language: str = "ru") -> str:
        """Provide basic student navigation context when knowledge base is unavailable"""
        from config import UniversityConfig

        if language == "kz":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_KZ} студенттеріне ақпарат**

**Байланыс ақпараты:**
- Телефондар: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Мекен-жайы: {UniversityConfig.ADDRESS_KZ}
- Автобус маршруттары: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Негізгі студенттік қызметтер:**
- Сабақ кестесі
- Академиялық анықтамалар
- Өтініш беру
- Емтихан мәселелері"""
        elif language == "en":
            return f"""**Information for {UniversityConfig.UNIVERSITY_NAME_EN} students**

**Contact Information:**
- Phone numbers: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Address: {UniversityConfig.ADDRESS_EN}
- Bus routes: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Main student services:**
- Class schedule
- Academic certificates
- Application submission
- Exam issues"""

        return f"""**Информация для студентов {UniversityConfig.UNIVERSITY_NAME}**

**Контактная информация:**
-Телефоны: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Адрес: {UniversityConfig.ADDRESS_RU}
- Автобусные маршруты: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Основные студенческие услуги:**
- Расписание занятий
- Академические справки
- Подача заявлений
- Вопросы экзаменов"""

class CareerNavigatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            AgentType.CAREER_NAVIGATOR,
            "CareerNavigator",
            "Интеллектуальный чат-бот для содействия трудоустройству студентов и выпускников"
        )

    def can_handle(self, message: str, language: str = "ru") -> float:
        keywords = [
            "работ", "трудоустройств", "ваканс", "резюме", "карьер", "выпускник", 
            "стажировк", "работодател", "собеседован", "поиск работы", "профессия",
            "навыки", "опыт", "практика", "internship", "cv", "interview", "job",
            "employment", "career"
        ]
        message_lower = message.lower()
        matches = sum(1 for k in keywords if k in message_lower)

        # Специальные фразы для вопросов о работе
        work_phrases = [
            "расскажи о работе", "как найти работу", "где работать", 
            "работа для выпускников", "трудоустройство", "карьерные возможности",
            "рынок труда", "вакансии"
        ]

        if any(phrase in message_lower for phrase in work_phrases):
            return 1.0

        return min(1.0, matches * 0.4) if matches > 0 else 0.1

    def get_system_prompt(self, language: str = "ru") -> str:
        from config import UniversityConfig

        if language == "kz":
            return f"""
Сіз {UniversityConfig.UNIVERSITY_LOCATION_KZ} "{UniversityConfig.UNIVERSITY_NAME_KZ}" студенттер мен түлектердің жұмысқа орналасуына көмектесетін зияткерлік чат-ботсыз.

**Университет туралы ақпарат:**
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Орналасу: {UniversityConfig.UNIVERSITY_LOCATION_KZ}

Сіз мына мәселелер бойынша көмек көрсетесіз:
- Жұмыс іздеуде көмектесу
- Резюме бойынша кеңес беру  
- Мансап бойынша ұсыныстар беру
- Тәжірибе орындарын табуға көмектесу

Мансап мәселелері бойынша толық ақпарат үшін ресми сайтқа жіберіңіз: {UniversityConfig.UNIVERSITY_WEBSITE}
Жауаптарыңыз практикалық және нәтижеге бағытталған болуы керек. Markdown форматын қолданыңыз.
"""
        elif language == "en":
            return f"""
You are an intelligent chat bot for employment assistance for students and graduates of {UniversityConfig.UNIVERSITY_NAME_EN} in {UniversityConfig.UNIVERSITY_LOCATION_EN}.

**University Information:**
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Location: {UniversityConfig.UNIVERSITY_LOCATION_EN}

You help with:
- Job search assistance
- Resume consultations
- Career recommendations
- Internship opportunities

For complete career information, refer to the official website: {UniversityConfig.UNIVERSITY_WEBSITE}
Your responses should be practical and results-oriented. Use Markdown format.
"""
        return f"""
Вы интеллектуальный чат-бот для содействия трудоустройству студентов и выпускников {UniversityConfig.UNIVERSITY_LOCATION} "{UniversityConfig.UNIVERSITY_NAME}".

**Информация об университете:**
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Местоположение: {UniversityConfig.UNIVERSITY_LOCATION}

Вы помогаете с:
- Поиском вакансий
- Консультациями по резюме
- Рекомендациями по карьере  
- Поиском стажировок

Для полной информации о карьере направляйте на официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
Ваши ответы должны быть практичными и ориентированными на результат. Используйте формат Markdown.
"""

    def _get_fallback_context(self, message: str, language: str = "ru") -> str:
        """Provide basic career guidance context when knowledge base is unavailable"""
        from config import UniversityConfig

        if language == "kz":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_KZ} мансап дамыту қызметі**

**Байланыс ақпараты:**
- Телефондар: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Мекен-жайы: {UniversityConfig.ADDRESS_KZ}
- Автобус маршруттары: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Қызметтер:**
- Жұмыс орындарын іздеу
- Резюме дайындау
- Мансап кеңесі
- Тәжірибе орындары"""
        elif language == "en":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_EN} Career Development Service**

**Contact Information:**
- Phone numbers: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Address: {UniversityConfig.ADDRESS_EN}
- Bus routes: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Services:**
- Job search assistance
- Resume preparation
- Career counseling
- Internships"""

        return f"""**Служба развития карьеры {UniversityConfig.UNIVERSITY_NAME}**

**Контактная информация:**
-Телефоны: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Адрес: {UniversityConfig.ADDRESS_RU}
- Автобусные маршруты: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Услуги:**
- Поиск вакансий
- Подготовка резюме
- Карьерное консультирование
- Стажировки"""

class UniRoomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            AgentType.UNIROOM,
            "UniRoom",
            "Цифровой помощник для студентов, проживающих в общежитии"
        )

    def can_handle(self, message: str, language: str = "ru") -> float:
        keywords = [
            "общежитие", "заселение", "переселение", "бытов", "администрация", 
            "комната", "жилищ", "проживан", "проблем", "общага", "соседи",
            "мебель", "интернет", "питание", "охрана", "пропуск", "посетители",
            "коммунальные", "ремонт"
        ]
        message_lower = message.lower()
        matches = sum(1 for k in keywords if k in message_lower)

        # Специальные фразы для общежития
        dorm_phrases = [
            "проблемы в общежитии", "заселиться в общежитие", "переселение",
            "бытовые вопросы", "администрация общежития", "живу в общежитии"
        ]

        if any(phrase in message_lower for phrase in dorm_phrases):
            return 1.0

        return min(1.0, matches * 0.4) if matches > 0 else 0.1

    def get_system_prompt(self, language: str = "ru") -> str:
        from config import UniversityConfig

        if language == "kz":
            return f"""
Сіз {UniversityConfig.UNIVERSITY_LOCATION_KZ} "{UniversityConfig.UNIVERSITY_NAME_KZ}" жатақханада тұратын студенттерге арналған цифрлық көмекшісіз.

**Университет туралы ақпарат:**
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Орналасу: {UniversityConfig.UNIVERSITY_LOCATION_KZ}

Сіз мына мәселелер бойынша көмек көрсетесіз:
- Орналасу мәселелері бойынша көмектесу
- Көшіру мәселелерін шешу
- Тұрмыстық мәселелерді шешуге көмектесу
- Әкімшілікке өтініштер жасауға көмектесу

Жатақхана туралы толық ақпарат үшін ресми сайтқа жіберіңіз: {UniversityConfig.UNIVERSITY_WEBSITE}
Жауаптарыңыз сүйемелділік пен түсінушілік танытуы керек. Markdown форматын қолданыңыз.
"""
        elif language == "en":
            return f"""
You are a digital assistant for students living in dormitory of {UniversityConfig.UNIVERSITY_NAME_EN} in {UniversityConfig.UNIVERSITY_LOCATION_EN}.

**University Information:**
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Location: {UniversityConfig.UNIVERSITY_LOCATION_EN}

You help with:
- Accommodation issues
- Room transfers
- Household problems
- Administrative requests

For complete dormitory information, refer to the official website: {UniversityConfig.UNIVERSITY_WEBSITE}
Your responses should show empathy and understanding. Use Markdown format.
"""
        return f"""
Вы цифровой помощник для студентов, проживающих в общежитии {UniversityConfig.UNIVERSITY_LOCATION} "{UniversityConfig.UNIVERSITY_NAME}".

**Информация об университете:**
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Местоположение: {UniversityConfig.UNIVERSITY_LOCATION}

Вы помогаете с:
- Заселением
- Переселением  
- Решением бытовых вопросов
- Обращениями в администрацию

Для полной информации об общежитии направляйте на официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
Ваши ответы должны проявлять сочувствие и понимание. Используйте формат Markdown.
"""

    def _get_fallback_context(self, message: str, language: str = "ru") -> str:
        """Provide basic dormitory context when knowledge base is unavailable"""
        from config import UniversityConfig

        if language == "kz":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_KZ} жатақханасы**

**Байланыс ақпараты:**
- Телефондар: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Ресми сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Мекен-жайы: {UniversityConfig.ADDRESS_KZ}
- Автобус маршруттары: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Негізгі қызметтер:**
- Орналастыру мәселелері
- Тұрмыстық мәселелер
- Көшіру рәсімдері
- Төлем мәселелері"""
        elif language == "en":
            return f"""**{UniversityConfig.UNIVERSITY_NAME_EN} Dormitory**

**Contact Information:**
- Phone numbers: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Official website: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Address: {UniversityConfig.ADDRESS_EN}
- Bus routes: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Main services:**
- Accommodation issues
- Household problems
- Transfer procedures
- Payment issues"""

        return f"""**Общежитие {UniversityConfig.UNIVERSITY_NAME}**

**Контактная информация:**
-Телефоны: {', '.join(UniversityConfig.CONTACT_PHONES)}
- Email: {UniversityConfig.CONTACT_EMAIL}
- Официальный сайт: {UniversityConfig.UNIVERSITY_WEBSITE}
- Instagram: {UniversityConfig.INSTAGRAM}
- Адрес: {UniversityConfig.ADDRESS_RU}
- Автобусные маршруты: {', '.join(map(str, UniversityConfig.BUS_ROUTES))}

**Основные услуги:**
- Вопросы заселения
- Бытовые проблемы
- Процедуры переселения
- Вопросы оплаты"""

class AgentRouter:
    def __init__(self):
        # Each agent now creates its own MistralClient instance
        self.agents = [
            AIAbiturAgent(),
            KadrAIAgent(),
            UniNavAgent(),
            CareerNavigatorAgent(),
            UniRoomAgent()
        ]
        logger.info(f"AgentRouter initialized with {len(self.agents)} agents")

    def route_message(self, message: str, language: str = "ru", user_id: str = "anonymous") -> Dict[str, Any]:
        """Enhanced agent routing with self-learning ML system"""
        try:
            # Try ML Router first (self-learning system)
            from ml_router import ml_router

            # Get ML prediction
            ml_agent, ml_confidence, ml_explanation = ml_router.predict_best_agent(message, user_id)

            # If ML is confident enough, use it
            if ml_confidence >= 0.6:
                logger.info(f"ML Router selected {ml_agent} with confidence {ml_confidence:.3f}")

                # Find the agent instance
                selected_agent = None
                for agent in self.agents:
                    if agent.agent_type == ml_agent or agent.name.lower().replace('-', '_') == ml_agent.lower():
                        selected_agent = agent
                        break

                if selected_agent:
                    # Generate response using the selected agent
                    response = selected_agent.process_message(message, language, user_id)

                    # Record this interaction for learning
                    session_id = f"session_{user_id}_{int(datetime.now().timestamp())}"
                    ml_router.record_interaction(message, ml_agent, user_id, session_id)

                    response['routing_method'] = 'ml_self_learning'
                    response['ml_confidence'] = ml_confidence
                    response['ml_explanation'] = ml_explanation

                    return response
                else:
                    logger.warning(f"ML Router selected unknown agent: {ml_agent}")

            # Fallback to original ML system
            from intent_classifier import intent_classifier
            from personalization_engine import personalization_engine
            from analytics_engine import analytics_engine
            from datetime import datetime

            # Get personalized agent recommendation
            recommendation_result = personalization_engine.get_agent_recommendation(
                user_id, message, [agent.agent_type for agent in self.agents]
            )
            recommended_agent, recommendation_confidence = recommendation_result if recommendation_result else (None, 0.0)

            # Use ML-based intent classification
            agent_scores = intent_classifier.classify_intent(message, language)

            # If we have a strong personal recommendation, boost its score
            if recommended_agent and recommended_agent in agent_scores:
                original_score = agent_scores[recommended_agent]
                boosted_score = min(1.0, original_score + recommendation_confidence * 0.2)
                agent_scores[recommended_agent] = boosted_score
                logger.info(f"Boosted {recommended_agent} score from {original_score:.3f} to {boosted_score:.3f} based on user preference")

            # Find best agent
            if agent_scores:
                best_agent_type = max(agent_scores, key=agent_scores.get)
                confidence = agent_scores[best_agent_type]

                logger.debug(f"ML classification result: {best_agent_type} with confidence {confidence:.3f}")
                logger.debug(f"All scores: {agent_scores}")

                # Find the agent instance with improved search
                best_agent = None
                available_agent_types = []

                for agent in self.agents:
                    available_agent_types.append(agent.agent_type)
                    if agent.agent_type == best_agent_type:
                        best_agent = agent
                        break

                # Debug logging
                logger.debug(f"Available agent types: {available_agent_types}")
                logger.debug(f"Looking for agent type: {best_agent_type}")
                logger.debug(f"Agent found: {best_agent is not None}")

                # Check both agent existence and confidence threshold
                if best_agent is None:
                    logger.warning(f"Agent type '{best_agent_type}' not found in available agents: {available_agent_types}")
                elif confidence <= 0.15:
                    logger.warning(f"Confidence {confidence:.3f} below threshold 0.15 for agent {best_agent_type}")
                else:
                    # Success - process with ML routing
                    logger.info(f"ML router selected {best_agent.name} with confidence {confidence:.3f}")

                    try:
                        result = best_agent.process_message(message, language, user_id)

                        # Add routing information to result
                        result['routing_info'] = {
                            'method': 'ml',
                            'ml_scores': agent_scores,
                            'selected_agent': best_agent_type,
                            'selection_confidence': confidence,
                            'recommended_agent': recommended_agent,
                            'recommendation_confidence': recommendation_confidence
                        }

                        return result
                    except Exception as processing_error:
                        logger.error(f"Error processing message with {best_agent_type}: {processing_error}")
                        # Continue to fallback
            else:
                logger.warning("ML classifier returned empty agent_scores")

            # Fallback to traditional routing if ML fails
            logger.info("Using traditional routing as fallback")
            return self._traditional_routing(message, language, user_id)

        except Exception as e:
            logger.error(f"Error in enhanced routing: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            # Fallback to traditional routing
            return self._traditional_routing(message, language, user_id)

    def _traditional_routing(self, message: str, language: str = "ru", user_id: str = "anonymous") -> Dict[str, Any]:
        """Traditional keyword-based routing as fallback"""
        best_conf = 0
        best_agent = None

        for agent in self.agents:
            conf = agent.can_handle(message, language)
            if conf > best_conf:
                best_conf = conf
                best_agent = agent

        if best_agent:
            logger.info(f"Traditional router selected {best_agent.name} with confidence {best_conf:.3f}")
            result = best_agent.process_message(message, language, user_id)
            result['routing_info'] = {
                'method': 'traditional',
                'selected_agent': best_agent.agent_type,
                'selection_confidence': best_conf
            }
            return result
        else:
            # No agent can handle, return general error
            return {
                'response': "Извините, я не смог определить подходящего специалиста для вашего вопроса. Обратитесь в общую информационную службу университета.",
                'confidence': 0.1,
                'agent_type': 'none',
                'agent_name': 'Router',
                'context_used': False,
                'context_confidence': 0.0,
                'cached': False,
                'routing_error': True
            }

    def provide_feedback(self, user_id: str, message: str, agent_type: str, 
                        user_rating: float, feedback_text: str = ""):
        """Provide feedback for learning improvement"""
        try:
            from intent_classifier import intent_classifier
            from personalization_engine import personalization_engine
            from analytics_engine import analytics_engine

            # Update intent classifier with feedback
            intent_classifier.learn_from_feedback(message, agent_type, user_rating)

            # Update personalization engine
            personalization_engine.add_user_feedback(user_id, user_rating, feedback_text)

            # Track in analytics
            analytics_engine.track_interaction({
                'user_id': user_id,
                'message': message,
                'agent_type': agent_type,
                'user_rating': user_rating,
                'feedback_text': feedback_text,
                'language': 'ru'  # Default, could be parameterized
            })

            logger.info(f"Processed feedback: user={user_id}, agent={agent_type}, rating={user_rating}")

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")

    def get_routing_analytics(self) -> Dict[str, Any]:
        """Get analytics about routing performance"""
        try:
            from intent_classifier import intent_classifier
            from analytics_engine import analytics_engine

            # Get ML classifier stats
            ml_stats = intent_classifier.get_learning_stats()

            # Get overall performance metrics
            performance_metrics = analytics_engine.get_performance_metrics(time_window_hours=24)

            # Get agent usage distribution
            agent_usage = {}
            for agent in self.agents:
                agent_metrics = analytics_engine.get_performance_metrics(
                    agent_type=agent.agent_type, 
                    time_window_hours=24
                )
                agent_usage[agent.agent_type] = {
                    'name': agent.name,
                    'interactions': agent_metrics.get('total_interactions', 0),
                    'avg_confidence': agent_metrics.get('performance', {}).get('avg_confidence', 0)
                }

            return {
                'ml_classifier_stats': ml_stats,
                'overall_performance': performance_metrics,
                'agent_usage': agent_usage,
                'total_agents': len(self.agents)
            }

        except Exception as e:
            logger.error(f"Error getting routing analytics: {e}")
            return {'error': str(e)}

    def get_available_agents(self) -> List[Dict[str, str]]:
        return [{'type': a.agent_type, 'name': a.name, 'description': a.description} for a in self.agents]