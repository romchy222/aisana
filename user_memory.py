
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from models import UserContext, UserQuery, db
from sqlalchemy import func, desc

logger = logging.getLogger(__name__)

class UserMemoryManager:
    """Manages user context and memory across chat sessions"""
    
    def __init__(self):
        self.context_cache = {}  # In-memory cache for active sessions
        
    def get_or_create_context(self, session_id: str, user_id: str = 'anonymous') -> UserContext:
        """Get existing user context or create new one"""
        try:
            context = UserContext.query.filter_by(session_id=session_id).first()
            
            if not context:
                context = UserContext(
                    session_id=session_id,
                    user_id=user_id,
                    first_interaction=datetime.utcnow(),
                    last_interaction=datetime.utcnow()
                )
                db.session.add(context)
                db.session.commit()
                logger.info(f"Created new user context for session: {session_id}")
            
            return context
        except Exception as e:
            logger.error(f"Error getting/creating user context: {str(e)}")
            # Return a temporary context object if database fails
            return UserContext(session_id=session_id, user_id=user_id)
    
    def extract_user_info(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Extract user information from message using pattern matching"""
        extracted_info = {}
        message_lower = message.lower()
        
        # Extract name patterns
        name_patterns = [
            r'меня зовут\s+([А-Яа-яЁё]+(?:\s+[А-Яа-яЁё]+)?)',
            r'мое имя\s+([А-Яа-яЁё]+(?:\s+[А-Яа-яЁё]+)?)',
            r'я\s+([А-Яа-яЁё]{3,})',
            r'менің атым\s+([А-Яа-яЁё]+(?:\s+[А-Яа-яЁё]+)?)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message)
            if match:
                potential_name = match.group(1).strip()
                # Avoid common words that aren't names
                if potential_name not in ['студент', 'хочу', 'могу', 'буду', 'была', 'будет']:
                    extracted_info['name'] = potential_name.title()
                    break
        
        # Extract interests/topics
        interest_keywords = {
            'поступление': ['поступление', 'поступить', 'подача документов', 'зачисление'],
            'стипендия': ['стипендия', 'грант', 'финансовая помощь'],
            'общежитие': ['общежитие', 'жатақхана', 'проживание', 'комната'],
            'расписание': ['расписание', 'занятия', 'лекции', 'пары'],
            'карьера': ['работа', 'трудоустройство', 'карьера', 'практика', 'стажировка'],
            'академические': ['экзамены', 'зачеты', 'оценки', 'кредиты', 'семестр']
        }
        
        detected_interests = []
        for interest, keywords in interest_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_interests.append(interest)
        
        if detected_interests:
            extracted_info['interests'] = detected_interests
        
        # Extract preferences
        if any(word in message_lower for word in ['казахский', 'қазақша', 'казахский язык']):
            extracted_info['language_preference'] = 'kz'
        elif any(word in message_lower for word in ['английский', 'english', 'english language']):
            extracted_info['language_preference'] = 'en'
        
        return extracted_info
    
    def update_context(self, session_id: str, user_message: str, bot_response: str, 
                      agent_name: str = None) -> UserContext:
        """Update user context with new interaction"""
        try:
            context = self.get_or_create_context(session_id)
            
            # Extract information from user message
            extracted_info = self.extract_user_info(user_message, context)
            
            # Update name if extracted
            if 'name' in extracted_info and not context.name:
                context.name = extracted_info['name']
            
            # Update interests
            if 'interests' in extracted_info:
                current_interests = context.interests or []
                new_interests = extracted_info['interests']
                # Merge interests without duplicates
                merged_interests = list(set(current_interests + new_interests))
                context.interests = merged_interests
            
            # Update language preference
            if 'language_preference' in extracted_info:
                context.language_preference = extracted_info['language_preference']
            
            # Update preferences
            if not context.preferences:
                context.preferences = {}
            
            # Track favorite agent
            if agent_name:
                agent_usage = context.preferences.get('agent_usage', {})
                agent_usage[agent_name] = agent_usage.get(agent_name, 0) + 1
                context.preferences['agent_usage'] = agent_usage
                
                # Set favorite agent
                context.favorite_agent = max(agent_usage.items(), key=lambda x: x[1])[0]
            
            # Update context summary (keep last 3 interactions summary)
            summary_parts = []
            if context.context_summary:
                summary_parts.append(context.context_summary)
            
            # Add current interaction summary
            interaction_summary = f"Пользователь спрашивал о: {user_message[:100]}..."
            summary_parts.append(interaction_summary)
            
            # Keep only last 3 summaries to avoid too long context
            if len(summary_parts) > 3:
                summary_parts = summary_parts[-3:]
            
            context.context_summary = " | ".join(summary_parts)
            
            # Update counters and timestamps
            context.total_messages += 1
            context.last_interaction = datetime.utcnow()
            context.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Cache the context
            self.context_cache[session_id] = context
            
            logger.info(f"Updated context for session {session_id}: name={context.name}, interests={context.interests}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error updating user context: {str(e)}")
            return self.get_or_create_context(session_id)
    
    def get_context_for_ai(self, session_id: str) -> str:
        """Get formatted context for AI agent"""
        try:
            context = UserContext.query.filter_by(session_id=session_id).first()
            
            if not context:
                return ""
            
            context_parts = []
            
            # Add user name
            if context.name:
                context_parts.append(f"Пользователя зовут {context.name}")
            
            # Add interests
            if context.interests:
                interests_str = ", ".join(context.interests)
                context_parts.append(f"Интересуется: {interests_str}")
            
            # Add favorite agent
            if context.favorite_agent:
                context_parts.append(f"Чаще всего обращается к агенту: {context.favorite_agent}")
            
            # Add language preference
            if context.language_preference and context.language_preference != 'ru':
                lang_map = {'kz': 'казахский', 'en': 'английский'}
                lang_name = lang_map.get(context.language_preference, context.language_preference)
                context_parts.append(f"Предпочитает язык: {lang_name}")
            
            # Add recent context
            if context.context_summary:
                context_parts.append(f"Контекст предыдущих разговоров: {context.context_summary}")
            
            # Add interaction stats
            if context.total_messages > 1:
                context_parts.append(f"Общался с системой {context.total_messages} раз")
            
            if context_parts:
                return "КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:\n" + "\n".join(f"- {part}" for part in context_parts) + "\n"
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting context for AI: {str(e)}")
            return ""
    
    def get_recent_history(self, session_id: str, limit: int = 5) -> List[Dict]:
        """Get recent chat history for context"""
        try:
            recent_queries = UserQuery.query.filter_by(session_id=session_id)\
                .order_by(desc(UserQuery.created_at))\
                .limit(limit).all()
            
            history = []
            for query in reversed(recent_queries):  # Reverse to chronological order
                history.append({
                    'user_message': query.user_message,
                    'bot_response': query.bot_response,
                    'agent_name': query.agent_name,
                    'timestamp': query.created_at.isoformat() if query.created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting recent history: {str(e)}")
            return []
    
    def clear_context(self, session_id: str):
        """Clear user context"""
        try:
            context = UserContext.query.filter_by(session_id=session_id).first()
            if context:
                db.session.delete(context)
                db.session.commit()
                
            # Remove from cache
            if session_id in self.context_cache:
                del self.context_cache[session_id]
                
            logger.info(f"Cleared context for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing context: {str(e)}")

# Global instance
user_memory = UserMemoryManager()
