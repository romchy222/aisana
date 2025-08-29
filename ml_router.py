#!/usr/bin/env python3
"""
ML Router с самообучением на основе истории взаимодействий
Adaptive Machine Learning Router for BolashakChat
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class InteractionRecord:
    """Запись о взаимодействии пользователя с агентом"""
    message: str
    selected_agent: str
    user_rating: Optional[int]  # 1-5 stars
    response_relevance: float   # 0-1 calculated relevance
    timestamp: datetime
    user_id: str
    session_id: str
    message_hash: str

@dataclass
class AgentPerformance:
    """Производительность агента для конкретного типа вопросов"""
    agent_name: str
    message_pattern: str
    success_rate: float
    avg_rating: float
    interaction_count: int
    last_updated: datetime

class MLRouter:
    """
    Самообучающийся маршрутизатор агентов
    Использует историю взаимодействий для улучшения качества маршрутизации
    """
    
    def __init__(self, db_path: str = "ml_router_history.db"):
        self.db_path = db_path
        self.feature_extractors = []
        self.agent_patterns = defaultdict(list)
        self.performance_cache = {}
        self.min_confidence_threshold = 0.3
        self.learning_rate = 0.1
        
        # Инициализация базы данных
        self._init_database()
        
        # Загрузка истории
        self._load_historical_data()
        
        # Автоинициализация если нет паттернов
        if len(self.performance_cache) == 0:
            self._auto_initialize_patterns()
        
        logger.info(f"ML Router initialized with {len(self.agent_patterns)} agent patterns")
    
    def _init_database(self):
        """Инициализация базы данных для хранения истории"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_hash TEXT UNIQUE,
                        message TEXT NOT NULL,
                        selected_agent TEXT NOT NULL,
                        user_rating INTEGER,
                        response_relevance REAL,
                        timestamp TEXT NOT NULL,
                        user_id TEXT,
                        session_id TEXT,
                        feedback_type TEXT DEFAULT 'implicit'
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_name TEXT NOT NULL,
                        message_pattern TEXT NOT NULL,
                        success_rate REAL DEFAULT 0.0,
                        avg_rating REAL DEFAULT 0.0,
                        interaction_count INTEGER DEFAULT 0,
                        last_updated TEXT NOT NULL,
                        UNIQUE(agent_name, message_pattern)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS learning_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                logger.info("ML Router database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize ML Router database: {e}")
    
    def _load_historical_data(self):
        """Загрузка исторических данных для обучения"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Загружаем производительность агентов
                cursor = conn.execute("""
                    SELECT agent_name, message_pattern, success_rate, avg_rating, 
                           interaction_count, last_updated 
                    FROM agent_performance
                    WHERE interaction_count >= 5  -- Минимум 5 взаимодействий для надежности
                    ORDER BY success_rate DESC, avg_rating DESC
                """)
                
                for row in cursor:
                    agent_name, pattern, success_rate, avg_rating, count, last_updated = row
                    
                    performance = AgentPerformance(
                        agent_name=agent_name,
                        message_pattern=pattern,
                        success_rate=success_rate,
                        avg_rating=avg_rating,
                        interaction_count=count,
                        last_updated=datetime.fromisoformat(last_updated)
                    )
                    
                    self.performance_cache[f"{agent_name}:{pattern}"] = performance
                    self.agent_patterns[agent_name].append(pattern)
                
                logger.info(f"Loaded {len(self.performance_cache)} performance records")
                
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
    
    def _extract_message_features(self, message: str) -> Dict[str, float]:
        """Извлечение признаков из сообщения"""
        message_lower = message.lower().strip()
        
        features = {
            'length': len(message) / 100.0,  # Нормализованная длина
            'word_count': len(message.split()) / 20.0,  # Нормализованное количество слов
            'question_words': sum(1 for w in ['как', 'что', 'где', 'когда', 'почему', 'какой'] 
                                if w in message_lower) / 6.0,
            'urgency_indicators': sum(1 for w in ['срочно', 'быстро', 'немедленно', 'нужно'] 
                                    if w in message_lower) / 4.0,
            'formal_tone': sum(1 for w in ['пожалуйста', 'благодарю', 'уважаемый'] 
                             if w in message_lower) / 3.0,
        }
        
        # Доменные признаки
        domain_keywords = {
            'academic': ['расписание', 'экзамен', 'зачет', 'лекция', 'семинар', 'учеба', 'студент'],
            'career': ['работа', 'вакансии', 'резюме', 'карьера', 'трудоустройство'],
            'admission': ['поступление', 'абитуриент', 'документы', 'вступительный'],
            'hr': ['отпуск', 'зарплата', 'кадры', 'сотрудник', 'преподаватель'],
            'housing': ['общежитие', 'комната', 'заселение', 'проживание']
        }
        
        for domain, keywords in domain_keywords.items():
            features[f'domain_{domain}'] = sum(1 for kw in keywords 
                                             if kw in message_lower) / len(keywords)
        
        return features
    
    def _calculate_pattern_similarity(self, message: str, pattern: str) -> float:
        """Вычисление семантического сходства между сообщением и паттерном"""
        # Простая реализация на основе пересечения слов
        # В продакшене можно заменить на sentence embeddings
        
        message_words = set(message.lower().split())
        pattern_words = set(pattern.lower().split())
        
        if not message_words or not pattern_words:
            return 0.0
        
        intersection = len(message_words.intersection(pattern_words))
        union = len(message_words.union(pattern_words))
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Бонус за точные фразовые совпадения
        phrase_bonus = 0.0
        if pattern.lower() in message.lower() or message.lower() in pattern.lower():
            phrase_bonus = 0.3
        
        return min(1.0, jaccard_similarity + phrase_bonus)
    
    def predict_best_agent(self, message: str, user_id: str = "anonymous") -> Tuple[str, float, Dict[str, Any]]:
        """
        Предсказание лучшего агента на основе ML модели и истории
        
        Returns:
            Tuple[agent_name, confidence, explanation]
        """
        features = self._extract_message_features(message)
        agent_scores = defaultdict(float)
        explanations = defaultdict(list)
        
        # Анализируем производительность каждого агента
        for agent_name, patterns in self.agent_patterns.items():
            agent_score = 0.0
            pattern_matches = []
            
            for pattern in patterns:
                cache_key = f"{agent_name}:{pattern}"
                if cache_key in self.performance_cache:
                    performance = self.performance_cache[cache_key]
                    
                    # Вычисляем сходство с паттерном
                    similarity = self._calculate_pattern_similarity(message, pattern)
                    
                    if similarity > 0.1:  # Минимальное сходство
                        # Вес основан на исторической производительности
                        pattern_weight = (
                            performance.success_rate * 0.4 +
                            (performance.avg_rating / 5.0) * 0.3 +
                            min(performance.interaction_count / 100.0, 1.0) * 0.3
                        )
                        
                        pattern_score = similarity * pattern_weight
                        agent_score += pattern_score
                        
                        pattern_matches.append({
                            'pattern': pattern,
                            'similarity': similarity,
                            'performance': performance.success_rate,
                            'rating': performance.avg_rating,
                            'count': performance.interaction_count,
                            'score': pattern_score
                        })
            
            if pattern_matches:
                agent_scores[agent_name] = agent_score / len(patterns)  # Нормализация
                explanations[agent_name] = pattern_matches
        
        # Если ML модель не дала результатов, используем fallback
        if not agent_scores:
            return self._fallback_prediction(message, features)
        
        # Выбираем лучшего агента
        best_agent = max(agent_scores.items(), key=lambda x: x[1])
        agent_name, confidence = best_agent
        
        # Формируем объяснение
        explanation = {
            'method': 'ml_history',
            'all_scores': dict(agent_scores),
            'features': features,
            'best_matches': explanations[agent_name],
            'confidence_threshold': self.min_confidence_threshold
        }
        
        # Проверяем минимальный порог уверенности
        if confidence < self.min_confidence_threshold:
            fallback_agent, fallback_conf, fallback_exp = self._fallback_prediction(message, features)
            explanation['fallback_used'] = True
            explanation['fallback_reason'] = f"ML confidence {confidence:.3f} below threshold {self.min_confidence_threshold}"
            return fallback_agent, fallback_conf, explanation
        
        return agent_name, confidence, explanation
    
    def _fallback_prediction(self, message: str, features: Dict[str, float]) -> Tuple[str, float, Dict[str, Any]]:
        """Резервная логика предсказания когда ML модель не уверена"""
        message_lower = message.lower()
        
        # Простые правила на основе доменов
        domain_rules = [
            (['работа', 'трудоустройство', 'вакансии', 'резюме', 'карьера'], 'career_navigator', 0.8),
            (['расписание', 'экзамен', 'зачет', 'учеба', 'студент', 'система поддержки'], 'uninav', 0.7),
            (['поступление', 'абитуриент', 'документы', 'вступительный'], 'ai_abitur', 0.7),
            (['отпуск', 'зарплата', 'кадры', 'сотрудник', 'преподаватель'], 'kadrai', 0.7),
            (['общежитие', 'комната', 'заселение', 'проживание'], 'uniroom', 0.7)
        ]
        
        for keywords, agent, base_confidence in domain_rules:
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > 0:
                confidence = min(0.9, base_confidence * (matches / len(keywords)))
                explanation = {
                    'method': 'fallback_rules',
                    'matched_keywords': [kw for kw in keywords if kw in message_lower],
                    'match_ratio': matches / len(keywords),
                    'base_confidence': base_confidence
                }
                return agent, confidence, explanation
        
        # Если ничего не подошло, возвращаем UniNav как универсального агента
        return 'uninav', 0.4, {
            'method': 'default_fallback',
            'reason': 'No specific patterns matched'
        }
    
    def record_interaction(self, message: str, selected_agent: str, user_id: str, 
                          session_id: str, user_rating: Optional[int] = None,
                          response_relevance: Optional[float] = None) -> bool:
        """Записываем взаимодействие для обучения"""
        try:
            message_hash = hashlib.md5(message.encode()).hexdigest()
            timestamp = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO interactions 
                    (message_hash, message, selected_agent, user_rating, response_relevance,
                     timestamp, user_id, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (message_hash, message, selected_agent, user_rating, 
                      response_relevance, timestamp, user_id, session_id))
                
                conn.commit()
            
            # Асинхронное обновление модели
            self._update_model_async(message, selected_agent, user_rating, response_relevance)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")
            return False
    
    def _update_model_async(self, message: str, agent: str, rating: Optional[int], 
                           relevance: Optional[float]):
        """Асинхронное обновление модели на основе новых данных"""
        try:
            # Извлекаем ключевые фразы из сообщения для создания паттернов
            message_pattern = self._extract_pattern(message)
            
            # Обновляем производительность агента для данного паттерна
            cache_key = f"{agent}:{message_pattern}"
            
            if cache_key in self.performance_cache:
                perf = self.performance_cache[cache_key]
                
                # Обновляем метрики с learning rate
                if rating:
                    new_rating = perf.avg_rating * (1 - self.learning_rate) + (rating / 5.0) * self.learning_rate
                    perf.avg_rating = new_rating
                
                if relevance:
                    new_success_rate = perf.success_rate * (1 - self.learning_rate) + relevance * self.learning_rate
                    perf.success_rate = new_success_rate
                
                perf.interaction_count += 1
                perf.last_updated = datetime.now()
            else:
                # Создаем новую запись
                perf = AgentPerformance(
                    agent_name=agent,
                    message_pattern=message_pattern,
                    success_rate=relevance if relevance else 0.5,
                    avg_rating=(rating / 5.0) if rating else 0.5,
                    interaction_count=1,
                    last_updated=datetime.now()
                )
                
                self.performance_cache[cache_key] = perf
                self.agent_patterns[agent].append(message_pattern)
            
            # Сохраняем в базу данных
            self._save_performance_to_db(perf)
            
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
    
    def _extract_pattern(self, message: str) -> str:
        """Извлекает ключевой паттерн из сообщения для обучения"""
        # Упрощенная экстракция паттерна
        # В продакшене можно использовать более сложные NLP методы
        
        words = message.lower().split()
        
        # Убираем стоп-слова
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'как', 'что', 'где', 'когда', 'я', 'мне', 'меня'}
        important_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Берем первые 3-4 важных слова
        pattern = ' '.join(important_words[:4])
        
        return pattern if pattern else message[:50]  # fallback
    
    def _save_performance_to_db(self, performance: AgentPerformance):
        """Сохранение производительности агента в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO agent_performance 
                    (agent_name, message_pattern, success_rate, avg_rating,
                     interaction_count, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (performance.agent_name, performance.message_pattern,
                      performance.success_rate, performance.avg_rating,
                      performance.interaction_count, performance.last_updated.isoformat()))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save performance to DB: {e}")
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Получение статистики обучения модели"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Общая статистика
                cursor = conn.execute("SELECT COUNT(*) FROM interactions")
                total_interactions = cursor.fetchone()[0]
                
                # Статистика по агентам
                cursor = conn.execute("""
                    SELECT selected_agent, COUNT(*), AVG(user_rating), AVG(response_relevance)
                    FROM interactions 
                    WHERE user_rating IS NOT NULL OR response_relevance IS NOT NULL
                    GROUP BY selected_agent
                """)
                
                agent_stats = {}
                for row in cursor:
                    agent, count, avg_rating, avg_relevance = row
                    agent_stats[agent] = {
                        'interactions': count,
                        'avg_rating': avg_rating or 0,
                        'avg_relevance': avg_relevance or 0
                    }
                
                # Последние обновления
                cursor = conn.execute("""
                    SELECT agent_name, COUNT(*), MAX(last_updated)
                    FROM agent_performance
                    GROUP BY agent_name
                """)
                
                model_updates = {}
                for row in cursor:
                    agent, pattern_count, last_update = row
                    model_updates[agent] = {
                        'pattern_count': pattern_count,
                        'last_update': last_update
                    }
                
                return {
                    'total_interactions': total_interactions,
                    'agent_statistics': agent_stats,
                    'model_updates': model_updates,
                    'cached_patterns': len(self.performance_cache),
                    'confidence_threshold': self.min_confidence_threshold,
                    'learning_rate': self.learning_rate
                }
                
        except Exception as e:
            logger.error(f"Failed to get learning statistics: {e}")
            return {}
    
    def _auto_initialize_patterns(self):
        """Автоматическая инициализация базовых паттернов при первом запуске"""
        try:
            logger.info("Auto-initializing ML Router with basic patterns...")
            
            basic_patterns = [
                ("работа вакансии", "career_navigator", 5, 0.9),
                ("расписание занятий", "uninav", 5, 0.9),
                ("поступление документы", "ai_abitur", 5, 0.9),
                ("общежитие заселение", "uniroom", 5, 0.9),
                ("зарплата отпуск", "kadrai", 5, 0.9),
            ]
            
            for message, agent, rating, relevance in basic_patterns:
                self.record_interaction(
                    message=message,
                    selected_agent=agent,
                    user_id="auto_init",
                    session_id="auto_init_session",
                    user_rating=rating,
                    response_relevance=relevance
                )
            
            logger.info(f"Auto-initialized {len(basic_patterns)} basic patterns")
            
        except Exception as e:
            logger.error(f"Failed to auto-initialize patterns: {e}")

# Глобальный экземпляр ML Router
ml_router = MLRouter()