
#!/usr/bin/env python3
"""
Инициализация ML Router с базовыми паттернами обучения
"""

import sys
import os
sys.path.append('.')

from ml_router import ml_router
from datetime import datetime

def init_basic_patterns():
    """Инициализация базовых паттернов для ML Router"""
    
    print("🤖 Инициализация ML Router с базовыми паттернами...")
    
    # Базовые паттерны для каждого агента
    training_patterns = [
        # Career Navigator
        ("как найти работу", "career_navigator", 5, 0.9),
        ("вакансии для студентов", "career_navigator", 5, 0.9),
        ("резюме помощь", "career_navigator", 4, 0.8),
        ("трудоустройство выпускников", "career_navigator", 5, 0.9),
        ("карьерные возможности", "career_navigator", 4, 0.8),
        ("стажировки программы", "career_navigator", 4, 0.8),
        ("работодатели партнеры", "career_navigator", 4, 0.7),
        
        # UniNav (академические вопросы)
        ("расписание занятий", "uninav", 5, 0.9),
        ("экзамены когда", "uninav", 5, 0.9),
        ("зачеты расписание", "uninav", 5, 0.9),
        ("учебный план", "uninav", 4, 0.8),
        ("лекции семинары", "uninav", 4, 0.8),
        ("система поддержки студентов", "uninav", 4, 0.8),
        ("академический календарь", "uninav", 4, 0.7),
        ("библиотека доступ", "uninav", 4, 0.7),
        
        # AI Abitur (поступление)
        ("как поступить", "ai_abitur", 5, 0.9),
        ("документы поступление", "ai_abitur", 5, 0.9),
        ("абитуриент информация", "ai_abitur", 5, 0.9),
        ("вступительные экзамены", "ai_abitur", 5, 0.9),
        ("требования поступления", "ai_abitur", 4, 0.8),
        ("специальности факультеты", "ai_abitur", 4, 0.8),
        ("сроки подачи документов", "ai_abitur", 4, 0.8),
        ("проходные баллы", "ai_abitur", 4, 0.7),
        
        # Kadrai (HR вопросы)
        ("отпуск заявление", "kadrai", 5, 0.9),
        ("зарплата вопросы", "kadrai", 5, 0.9),
        ("кадровые документы", "kadrai", 5, 0.9),
        ("преподаватель вакансии", "kadrai", 4, 0.8),
        ("сотрудники информация", "kadrai", 4, 0.8),
        ("трудовой договор", "kadrai", 4, 0.7),
        ("больничный лист", "kadrai", 4, 0.7),
        
        # UniRoom (общежитие)
        ("общежитие заселение", "uniroom", 5, 0.9),
        ("комната проблемы", "uniroom", 5, 0.9),
        ("проживание условия", "uniroom", 4, 0.8),
        ("переселение общежитие", "uniroom", 4, 0.8),
        ("соседи конфликты", "uniroom", 4, 0.8),
        ("плата общежитие", "uniroom", 4, 0.7),
        ("бытовые вопросы", "uniroom", 4, 0.7),
    ]
    
    # Добавляем паттерны в систему
    success_count = 0
    for message, agent, rating, relevance in training_patterns:
        try:
            success = ml_router.record_interaction(
                message=message,
                selected_agent=agent,
                user_id="system_init",
                session_id="pattern_init",
                user_rating=rating,
                response_relevance=relevance
            )
            if success:
                success_count += 1
                print(f"✅ {message} → {agent}")
            else:
                print(f"❌ {message} → {agent}")
        except Exception as e:
            print(f"❌ Ошибка для '{message}': {e}")
    
    print(f"\n🎉 Успешно добавлено {success_count}/{len(training_patterns)} паттернов")
    
    # Проверяем статистику
    try:
        stats = ml_router.get_learning_statistics()
        print(f"\n📊 Статистика ML Router:")
        print(f"- Всего взаимодействий: {stats.get('total_interactions', 0)}")
        print(f"- Кэшированных паттернов: {stats.get('cached_patterns', 0)}")
        print(f"- Агентов с данными: {len(stats.get('agent_statistics', {}))}")
        
        for agent, data in stats.get('agent_statistics', {}).items():
            print(f"  • {agent}: {data['interactions']} взаимодействий, рейтинг {data['avg_rating']:.2f}")
            
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")

def test_predictions():
    """Тестирование предсказаний после инициализации"""
    
    print("\n🧪 Тестирование предсказаний:")
    print("-" * 50)
    
    test_cases = [
        "как найти работу для выпускников",
        "расписание экзаменов",
        "документы для поступления в университет",
        "проблемы с соседом в общежитии",
        "вопрос по зарплате преподавателя"
    ]
    
    for message in test_cases:
        try:
            agent, confidence, explanation = ml_router.predict_best_agent(message)
            print(f"'{message}'")
            print(f"  → Агент: {agent} (уверенность: {confidence:.3f})")
            print(f"  → Метод: {explanation.get('method', 'unknown')}")
            
            if 'best_matches' in explanation and explanation['best_matches']:
                best_match = explanation['best_matches'][0]
                print(f"  → Лучший паттерн: '{best_match['pattern']}' (сходство: {best_match['similarity']:.3f})")
            print()
            
        except Exception as e:
            print(f"❌ Ошибка предсказания для '{message}': {e}")

if __name__ == '__main__':
    print("="*70)
    print("ИНИЦИАЛИЗАЦИЯ ML ROUTER С БАЗОВЫМИ ПАТТЕРНАМИ")
    print("="*70)
    
    init_basic_patterns()
    test_predictions()
    
    print("\n" + "="*70)
    print("✅ ML Router инициализирован и готов к работе!")
    print("Система будет продолжать обучаться на основе реальных взаимодействий.")
    print("="*70)
