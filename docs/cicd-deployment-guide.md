# CI/CD Pipeline для BolashakChat

## Обзор

Данный документ описывает настройку CI/CD pipeline для проекта BolashakChat, которая автоматически проверяет готовность проекта к деплою.

## Компоненты CI/CD

### 1. GitHub Actions Workflow

**Файл:** `.github/workflows/cicd.yml`

Pipeline состоит из трех основных jobs:

#### 🔍 Проверка качества кода (quality-check)
- Проверка синтаксиса Python
- Анализ безопасности с помощью `bandit` и `safety`
- Проверка зависимостей на уязвимости

#### 🧪 Тестирование приложения (application-test)
- Инициализация базы данных
- Health Check приложения
- Проверка импорта всех модулей
- Тестирование работоспособности Flask приложения

#### 🚀 Проверка готовности к деплою (deployment-readiness)
- Проверка структуры проекта
- Конфигурация для продакшена
- Тестирование запуска с Gunicorn
- Генерация сводки готовности к деплою

### 2. API Endpoint для проверки деплоя

**URL:** `/api/deployment-readiness`

Предоставляет REST API для проверки готовности системы к деплою в реальном времени.

**Пример ответа:**
```json
{
  "overall_status": "healthy",
  "deployment_ready": true,
  "checks": {
    "database": {"status": "healthy", "message": "База данных доступна и отвечает"},
    "agents": {"status": "healthy", "message": "Доступно агентов: 5"},
    "environment": {"status": "healthy", "message": "Все переменные настроены"},
    "dependencies": {"status": "healthy", "message": "Python 3.12.3, Flask 3.1.1"},
    "configuration": {"status": "healthy", "message": "Конфигурация корректна"}
  },
  "recommendations": [
    "Проект готов к деплою",
    "Используйте Gunicorn для продакшена",
    "Настройте PostgreSQL для продакшена"
  ]
}
```

### 3. Standalone Script для проверки деплоя

**Файл:** `check_deployment.py`

Независимый скрипт для локальной проверки готовности к деплою.

**Использование:**
```bash
python check_deployment.py
```

**Функции:**
- Проверка версии Python (требуется 3.11+)
- Проверка установленных зависимостей
- Валидация структуры проекта
- Тестирование запуска приложения
- Проверка переменных окружения
- Анализ настроек безопасности
- Генерация JSON отчета

## Проверки готовности к деплою

### Критические проверки (должны пройти):
- ✅ Приложение запускается без ошибок
- ✅ База данных инициализируется
- ✅ Все зависимости установлены
- ✅ Структура проекта корректна
- ✅ Gunicorn может запустить приложение

### Рекомендуемые настройки для продакшена:
- 🔧 Переменные окружения настроены
- 🔒 Секретный ключ изменен с тестового
- 🗄️ PostgreSQL вместо SQLite
- 🌐 Reverse proxy (nginx) настроен
- 🔐 HTTPS сертификаты установлены

## Переменные окружения

Обязательные для продакшена:
```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
SESSION_SECRET=your-secure-session-secret
MISTRAL_API_KEY=your-mistral-api-key
```

Дополнительные:
```bash
FLASK_ENV=production
FLASK_DEBUG=False
```

## Запуск CI/CD

### Автоматический запуск:
- При push в ветку `main` или `master`
- При создании Pull Request
- Можно запустить вручную в GitHub Actions

### Локальная проверка:
```bash
# Установка зависимостей
pip install -r pyproject.toml

# Проверка готовности
python check_deployment.py

# Тестирование API
curl http://localhost:5000/api/deployment-readiness
```

## Деплой в продакшен

### Рекомендуемая конфигурация:

**1. Gunicorn**
```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 30 app:app
```

**2. Nginx (пример конфигурации)**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**3. Systemd Service**
```ini
[Unit]
Description=BolashakChat Flask App
After=network.target

[Service]
User=bolashak
WorkingDirectory=/path/to/BolashakChat
Environment=DATABASE_URL=postgresql://...
Environment=SESSION_SECRET=...
ExecStart=/path/to/venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Мониторинг

### Health Check endpoints:
- `/api/health` - Базовая проверка работоспособности
- `/api/deployment-readiness` - Полная проверка готовности

### Логирование:
- Логи приложения сохраняются в системный журнал
- Gunicorn логи доступны через systemd
- Настройте ротацию логов для продакшена

## Устранение неполадок

### Частые проблемы:

**1. Ошибка подключения к базе данных**
```bash
# Проверьте переменную DATABASE_URL
echo $DATABASE_URL

# Проверьте доступность PostgreSQL
psql $DATABASE_URL -c "SELECT 1;"
```

**2. Проблемы с зависимостями**
```bash
# Переустановка зависимостей
pip install --force-reinstall -r requirements.txt
```

**3. Ошибки импорта модулей**
```bash
# Проверьте PYTHONPATH
export PYTHONPATH=/path/to/BolashakChat:$PYTHONPATH
```

## Поддержка

Для получения помощи по настройке CI/CD:
1. Проверьте логи GitHub Actions
2. Запустите `check_deployment.py` локально
3. Проверьте API endpoint `/api/deployment-readiness`
4. Обратитесь к документации в `/docs/`

---

**Автор:** CI/CD Pipeline для BolashakChat  
**Дата:** 2025-01-03  
**Версия:** 1.0