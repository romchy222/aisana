#!/usr/bin/env python3
"""
Тест самообучающегося ML Router
"""

import sys
import os
sys.path.append('.')

from ml_router import ml_router

def test_ml_router():
    """Тестируем ML Router с самообучением"""
    
    print("="*70)
    print("ТЕСТИРОВАНИЕ САМООБУЧАЮЩЕГОСЯ ML ROUTER")
    print("="*70)
    
    test_cases = [
        "расскажи о работе",
        "как найти работу для выпускников", 
        "система поддержки студентов",
        "проблемы в общежитии",
        "как поступить в университет"
    ]
    
    print("\n1. Тестируем предсказания ML Router")
    print("-" * 50)
    
    for i, message in enumerate(test_cases, 1):
        print(f"\nТест {i}: '{message}'")
        
        try:
            agent, confidence, explanation = ml_router.predict_best_agent(message)
            print(f"Агент: {agent}")
            print(f"Уверенность: {confidence:.3f}")
            print(f"Метод: {explanation.get('method', 'unknown')}")
            
            if explanation.get('fallback_used'):
                print(f"Использован fallback: {explanation.get('fallback_reason')}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("\n2. Симуляция обучения")
    print("-" * 50)
    
    # Симулируем обучение на нескольких примерах
    training_examples = [
        ("расскажи о работе", "career_navigator", 5, True),
        ("вакансии для выпускников", "career_navigator", 4, True),
        ("расписание занятий", "uninav", 5, True),
        ("проблемы в общежитии", "uniroom", 4, True),
        ("документы для поступления", "ai_abitur", 5, True),
    ]
    
    print("Обучаем ML Router на примерах...")
    for message, agent, rating, helpful in training_examples:
        relevance = 1.0 if helpful else 0.2
        success = ml_router.record_interaction(
            message=message,
            selected_agent=agent,
            user_id="test_user",
            session_id="test_session",
            user_rating=rating,
            response_relevance=relevance
        )
        print(f"{'✅' if success else '❌'} {message} -> {agent} (рейтинг: {rating})")
    
    print("\n3. Проверяем обучение")
    print("-" * 50)
    
    # Повторно тестируем те же вопросы
    for i, message in enumerate(test_cases, 1):
        print(f"\nПосле обучения {i}: '{message}'")
        
        try:
            agent, confidence, explanation = ml_router.predict_best_agent(message)
            print(f"Агент: {agent}")
            print(f"Уверенность: {confidence:.3f}")
            print(f"Метод: {explanation.get('method', 'unknown')}")
            
            # Показываем лучшие совпадения если есть
            if 'best_matches' in explanation and explanation['best_matches']:
                best_match = explanation['best_matches'][0]
                print(f"Лучшее совпадение: '{best_match['pattern']}' (сходство: {best_match['similarity']:.3f})")
                print(f"Производительность: {best_match['performance']:.3f}, рейтинг: {best_match['rating']:.1f}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("\n4. Статистика обучения")
    print("-" * 50)
    
    try:
        stats = ml_router.get_learning_statistics()
        print(f"Всего взаимодействий: {stats.get('total_interactions', 0)}")
        print(f"Кэшированных паттернов: {stats.get('cached_patterns', 0)}")
        print(f"Порог уверенности: {stats.get('confidence_threshold', 0)}")
        print(f"Скорость обучения: {stats.get('learning_rate', 0)}")
        
        print("\nСтатистика по агентам:")
        for agent, data in stats.get('agent_statistics', {}).items():
            print(f"  {agent}: {data['interactions']} взаимодействий, рейтинг {data['avg_rating']:.2f}")
            
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
    
    print("\n" + "="*70)
    print("🤖 ML Router готов к самообучению!")
    print("Система будет улучшаться с каждым взаимодействием пользователей.")
    print("="*70)

if __name__ == '__main__':
    test_ml_router()