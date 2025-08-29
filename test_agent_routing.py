#!/usr/bin/env python3
"""
Тест системы маршрутизации агентов
"""

import sys
import os
sys.path.append('.')

from agents import AgentRouter
from intent_classifier import intent_classifier

def test_routing():
    """Тестируем маршрутизацию различных типов вопросов"""
    router = AgentRouter()
    
    test_cases = [
        # Вопросы о работе/карьере - должны идти к CareerNavigator
        {
            "message": "расскажи о работе",
            "expected_agent": "CareerNavigator",
            "description": "Общий вопрос о работе"
        },
        {
            "message": "как найти работу для выпускников",
            "expected_agent": "CareerNavigator", 
            "description": "Поиск работы для выпускников"
        },
        {
            "message": "какие есть вакансии",
            "expected_agent": "CareerNavigator",
            "description": "Вопрос о вакансиях"
        },
        
        # Студенческие вопросы - должны идти к UniNav
        {
            "message": "как работает система поддержки студентов",
            "expected_agent": "UniNav",
            "description": "Система поддержки студентов"
        },
        {
            "message": "расписание занятий",
            "expected_agent": "UniNav",
            "description": "Расписание занятий"
        },
        {
            "message": "где подать заявление",
            "expected_agent": "UniNav",
            "description": "Подача заявлений"
        },
        
        # Вопросы поступления - должны идти к AI-Abitur
        {
            "message": "как поступить в университет",
            "expected_agent": "AI-Abitur",
            "description": "Поступление в университет"
        },
        {
            "message": "документы для поступления",
            "expected_agent": "AI-Abitur",
            "description": "Документы для поступления"
        },
        
        # Кадровые вопросы - должны идти к KadrAI
        {
            "message": "оформить отпуск, я работаю преподавателем",
            "expected_agent": "KadrAI",
            "description": "Кадровый вопрос от преподавателя"
        },
        {
            "message": "вопросы по зарплате сотрудника",
            "expected_agent": "KadrAI", 
            "description": "Вопросы по зарплате"
        },
        
        # Вопросы общежития - должны идти к UniRoom
        {
            "message": "проблемы в общежитии",
            "expected_agent": "UniRoom",
            "description": "Проблемы в общежитии"
        },
        {
            "message": "заселиться в общежитие",
            "expected_agent": "UniRoom",
            "description": "Заселение в общежитие"
        }
    ]
    
    print("="*70)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ МАРШРУТИЗАЦИИ АГЕНТОВ")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nТест {i}: {test['description']}")
        print(f"Сообщение: '{test['message']}'")
        
        # Получаем результат маршрутизации
        try:
            result = router.route_message(test['message'], 'ru')
            selected_agent = result.get('agent_name', 'Unknown')
            confidence = result.get('confidence', 0.0)
            
            # Проверяем ML-классификатор отдельно
            ml_scores = intent_classifier.classify_intent(test['message'], 'ru')
            best_ml_agent = max(ml_scores.items(), key=lambda x: x[1]) if ml_scores else ('None', 0.0)
            
            print(f"Выбран агент: {selected_agent} (уверенность: {confidence:.3f})")
            print(f"ML классификатор: {best_ml_agent[0]} ({best_ml_agent[1]:.3f})")
            print(f"Все ML оценки: {ml_scores}")
            
            if selected_agent == test['expected_agent']:
                print(f"✅ ПРОЙДЕН - Ожидался {test['expected_agent']}")
                passed += 1
            else:
                print(f"❌ ПРОВАЛЕН - Ожидался {test['expected_agent']}, получен {selected_agent}")
                failed += 1
                
        except Exception as e:
            print(f"❌ ОШИБКА - {str(e)}")
            failed += 1
    
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*70)
    print(f"Пройдено: {passed}")
    print(f"Провалено: {failed}")
    print(f"Всего: {passed + failed}")
    
    if failed > 0:
        print(f"\n⚠️ Нужно исправить маршрутизацию для {failed} случаев")
    else:
        print(f"\n🎉 Все тесты пройдены успешно!")
    
    return failed == 0

if __name__ == '__main__':
    success = test_routing()
    sys.exit(0 if success else 1)