# Импорт необходимых модулей
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    """Модель категории для FAQ"""
    __tablename__ = 'categories'
    
    # Первичный ключ
    id = db.Column(db.Integer, primary_key=True)
    # Название категории на русском языке
    name_ru = db.Column(db.String(100), nullable=False)
    # Название категории на казахском языке
    name_kz = db.Column(db.String(100), nullable=False)
    # Описание категории на русском языке
    description_ru = db.Column(db.Text)
    # Описание категории на казахском языке
    description_kz = db.Column(db.Text)
    # Дата создания записи
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь один-ко-многим с FAQ
    faqs = db.relationship('FAQ', backref='category', lazy=True)
    
    def __repr__(self):
        """Строковое представление категории"""
        return f'<Category {self.name_ru}>'

class FAQ(db.Model):
    """Модель часто задаваемых вопросов"""
    __tablename__ = 'faqs'
    
    # Первичный ключ
    id = db.Column(db.Integer, primary_key=True)
    # Вопрос на русском языке
    question_ru = db.Column(db.Text, nullable=False)
    # Вопрос на казахском языке
    question_kz = db.Column(db.Text, nullable=False)
    # Ответ на русском языке
    answer_ru = db.Column(db.Text, nullable=False)
    # Ответ на казахском языке
    answer_kz = db.Column(db.Text, nullable=False)
    # Внешний ключ на категорию
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    # Статус активности FAQ
    is_active = db.Column(db.Boolean, default=True)
    # Дата создания записи
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Дата последнего обновления
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        """Строковое представление FAQ"""
        return f'<FAQ {self.question_ru[:50]}...>'

class UserQuery(db.Model):
    __tablename__ = 'user_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(5), nullable=False, default='ru')
    response_time = db.Column(db.Float)  # Response time in seconds
    
    # Agent tracking fields
    agent_type = db.Column(db.String(50))  # Type of agent that handled the query
    agent_name = db.Column(db.String(100))  # Name of the agent
    agent_confidence = db.Column(db.Float)  # Confidence score of the selected agent
    context_used = db.Column(db.Boolean, default=False)  # Whether FAQ context was used
    
    # Rating system fields
    user_rating = db.Column(db.String(10))  # 'like', 'dislike', or null
    rating_timestamp = db.Column(db.DateTime)  # When rating was given
    
    session_id = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserQuery {self.user_message[:30]}...>'

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # pdf, doc, txt, etc.
    file_size = db.Column(db.Integer)  # Size in bytes
    content_text = db.Column(db.Text)  # Extracted text content
    is_processed = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.title}>'

class WebSource(db.Model):
    __tablename__ = 'web_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    content_text = db.Column(db.Text)  # Extracted text content
    last_scraped = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    scrape_frequency = db.Column(db.String(20), default='daily')  # daily, weekly, manual
    added_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<WebSource {self.title}>'

class KnowledgeBase(db.Model):
    __tablename__ = 'knowledge_base'
    
    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(20), nullable=False)  # 'document', 'web', 'manual'
    source_id = db.Column(db.Integer)  # Foreign key to Document or WebSource
    content_chunk = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.JSON)  # Additional metadata like page numbers, sections, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<KnowledgeBase {self.source_type}:{self.source_id}>'

class AgentKnowledgeBase(db.Model):
    """Agent-specific knowledge base entries"""
    __tablename__ = 'agent_knowledge_base'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_type = db.Column(db.String(50), nullable=False)  # Type of agent this knowledge belongs to
    title = db.Column(db.String(200), nullable=False)
    content_ru = db.Column(db.Text, nullable=False)  # Content in Russian
    content_kz = db.Column(db.Text, nullable=False)  # Content in Kazakh
    content_en = db.Column(db.Text)  # Content in English (optional)
    keywords = db.Column(db.String(500))  # Search keywords
    priority = db.Column(db.Integer, default=1)  # Priority for ordering (1=highest)
    category = db.Column(db.String(100))  # Knowledge category
    tags = db.Column(db.String(300))  # Comma-separated tags
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)  # Featured knowledge entries
    created_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_content(self, language='ru'):
        """Get content in specific language with fallback"""
        if language == 'kz' and self.content_kz:
            return self.content_kz
        elif language == 'en' and self.content_en:
            return self.content_en
        else:
            return self.content_ru
    
    def __repr__(self):
        return f'<AgentKnowledgeBase {self.agent_type}:{self.title}>'

class AgentType(db.Model):
    """Model for agent types and their configurations"""
    __tablename__ = 'agent_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'admission', 'scholarship'
    name_ru = db.Column(db.String(100), nullable=False)  # Name in Russian
    name_kz = db.Column(db.String(100), nullable=False)  # Name in Kazakh
    name_en = db.Column(db.String(100))  # Name in English
    description_ru = db.Column(db.Text)  # Description in Russian
    description_kz = db.Column(db.Text)  # Description in Kazakh
    description_en = db.Column(db.Text)  # Description in English
    system_prompt_ru = db.Column(db.Text)  # System prompt in Russian
    system_prompt_kz = db.Column(db.Text)  # System prompt in Kazakh
    system_prompt_en = db.Column(db.Text)  # System prompt in English
    icon_class = db.Column(db.String(50))  # CSS icon class
    color_scheme = db.Column(db.String(20))  # Color scheme identifier
    priority = db.Column(db.Integer, default=1)  # Display priority
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with knowledge base
    knowledge_entries = db.relationship('AgentKnowledgeBase', 
                                      foreign_keys='AgentKnowledgeBase.agent_type',
                                      primaryjoin='AgentType.type_code == AgentKnowledgeBase.agent_type',
                                      backref='agent_type_obj',
                                      lazy='dynamic')
    
    def get_name(self, language='ru'):
        """Get name in specific language with fallback"""
        if language == 'kz' and self.name_kz:
            return self.name_kz
        elif language == 'en' and self.name_en:
            return self.name_en
        else:
            return self.name_ru
    
    def get_description(self, language='ru'):
        """Get description in specific language with fallback"""
        if language == 'kz' and self.description_kz:
            return self.description_kz
        elif language == 'en' and self.description_en:
            return self.description_en
        else:
            return self.description_ru
    
    def get_system_prompt(self, language='ru'):
        """Get system prompt in specific language with fallback"""
        if language == 'kz' and self.system_prompt_kz:
            return self.system_prompt_kz
        elif language == 'en' and self.system_prompt_en:
            return self.system_prompt_en
        else:
            return self.system_prompt_ru
    
    def __repr__(self):
        return f'<AgentType {self.type_code}:{self.name_ru}>'

class UserContext(db.Model):
    """Model for storing user chat context and memory"""
    __tablename__ = 'user_contexts'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.String(100), default='anonymous')
    
    # User information extracted from conversations
    name = db.Column(db.String(100))
    preferences = db.Column(db.JSON)  # User preferences like language, agent preference, etc.
    interests = db.Column(db.JSON)  # Topics user is interested in
    context_summary = db.Column(db.Text)  # Summary of recent conversations
    
    # Conversation metadata
    total_messages = db.Column(db.Integer, default=0)
    favorite_agent = db.Column(db.String(50))
    language_preference = db.Column(db.String(5), default='ru')
    
    # Timestamps
    first_interaction = db.Column(db.DateTime, default=datetime.utcnow)
    last_interaction = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert context to dictionary for AI processing"""
        return {
            'name': self.name,
            'preferences': self.preferences or {},
            'interests': self.interests or [],
            'context_summary': self.context_summary,
            'total_messages': self.total_messages,
            'favorite_agent': self.favorite_agent,
            'language_preference': self.language_preference,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None
        }
    
    def __repr__(self):
        return f'<UserContext {self.session_id}:{self.name or "Anonymous"}>'

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    documents = db.relationship('Document', backref='uploader', lazy=True)
    web_sources = db.relationship('WebSource', backref='creator', lazy=True)
    agent_knowledge = db.relationship('AgentKnowledgeBase', backref='creator', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'

# Модели для системы расписания

class Faculty(db.Model):
    """Модель факультета"""
    __tablename__ = 'faculties'
    
    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(200), nullable=False)  # Название на русском
    name_kz = db.Column(db.String(200), nullable=False)  # Название на казахском
    name_en = db.Column(db.String(200))  # Название на английском
    code = db.Column(db.String(20), unique=True, nullable=False)  # Код факультета (IT, ECON)
    description_ru = db.Column(db.Text)  # Описание на русском
    description_kz = db.Column(db.Text)  # Описание на казахском
    description_en = db.Column(db.Text)  # Описание на английском
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    groups = db.relationship('Group', backref='faculty', lazy=True)
    
    def get_name(self, language='ru'):
        """Получить название на указанном языке"""
        if language == 'kz' and self.name_kz:
            return self.name_kz
        elif language == 'en' and self.name_en:
            return self.name_en
        else:
            return self.name_ru
    
    def get_description(self, language='ru'):
        """Получить описание на указанном языке"""
        if language == 'kz' and self.description_kz:
            return self.description_kz
        elif language == 'en' and self.description_en:
            return self.description_en
        else:
            return self.description_ru
    
    def __repr__(self):
        return f'<Faculty {self.code}: {self.name_ru}>'

class Group(db.Model):
    """Модель группы студентов"""
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Название группы (IT-22, ECON-23)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Год поступления
    semester = db.Column(db.Integer, default=1)  # Текущий семестр
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи удалены - Schedule теперь использует group_name как строку
    
    def __repr__(self):
        return f'<Group {self.name}>'

class Subject(db.Model):
    """Модель предмета/дисциплины"""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(200), nullable=False)  # Название на русском
    name_kz = db.Column(db.String(200), nullable=False)  # Название на казахском
    name_en = db.Column(db.String(200))  # Название на английском
    code = db.Column(db.String(20), unique=True, nullable=False)  # Код предмета
    description_ru = db.Column(db.Text)  # Описание на русском
    description_kz = db.Column(db.Text)  # Описание на казахском
    description_en = db.Column(db.Text)  # Описание на английском
    credits = db.Column(db.Integer, default=3)  # Количество кредитов
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи удалены - Schedule теперь использует title как строку
    
    def get_name(self, language='ru'):
        """Получить название на указанном языке"""
        if language == 'kz' and self.name_kz:
            return self.name_kz
        elif language == 'en' and self.name_en:
            return self.name_en
        else:
            return self.name_ru
    
    def get_description(self, language='ru'):
        """Получить описание на указанном языке"""
        if language == 'kz' and self.description_kz:
            return self.description_kz
        elif language == 'en' and self.description_en:
            return self.description_en
        else:
            return self.description_ru
    
    def __repr__(self):
        return f'<Subject {self.code}: {self.name_ru}>'

class Teacher(db.Model):
    """Модель преподавателя"""
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)  # Имя
    last_name = db.Column(db.String(100), nullable=False)  # Фамилия
    middle_name = db.Column(db.String(100))  # Отчество
    email = db.Column(db.String(120), unique=True)  # Email
    phone = db.Column(db.String(20))  # Телефон
    position_ru = db.Column(db.String(200))  # Должность на русском
    position_kz = db.Column(db.String(200))  # Должность на казахском
    position_en = db.Column(db.String(200))  # Должность на английском
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи удалены - Schedule теперь использует instructor как строку
    
    @property
    def full_name(self):
        """Полное имя преподавателя"""
        if self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        else:
            return f"{self.last_name} {self.first_name}"
    
    def get_position(self, language='ru'):
        """Получить должность на указанном языке"""
        if language == 'kz' and self.position_kz:
            return self.position_kz
        elif language == 'en' and self.position_en:
            return self.position_en
        else:
            return self.position_ru
    
    def __repr__(self):
        return f'<Teacher {self.full_name}>'

class Schedule(db.Model):
    """Модель расписания занятий"""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Основная информация (соответствует реальной структуре БД)
    schedule_type = db.Column(db.String(50), nullable=False)  # lecture, practice, lab, exam
    title = db.Column(db.String(255), nullable=False)  # Название предмета/занятия
    description = db.Column(db.Text)  # Описание
    
    # Организационная информация
    faculty = db.Column(db.String(100))  # Факультет
    department = db.Column(db.String(100))  # Кафедра
    course_code = db.Column(db.String(20))  # Код курса
    group_name = db.Column(db.String(50))  # Название группы
    instructor = db.Column(db.String(200))  # Преподаватель
    
    # Время и место
    start_time = db.Column(db.DateTime, nullable=False)  # Время начала (с датой)
    end_time = db.Column(db.DateTime, nullable=False)  # Время окончания (с датой)
    location = db.Column(db.String(100))  # Локация
    room = db.Column(db.String(50))  # Комната/аудитория
    
    # Повторяемость
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(100))  # Паттерн повторения
    
    # Статусы
    is_active = db.Column(db.Boolean, default=True)
    is_cancelled = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.Text)
    
    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def duration_minutes(self):
        """Длительность занятия в минутах"""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return 0
    
    @property
    def date(self):
        """Получить дату из start_time"""
        return self.start_time.date() if self.start_time else None
    
    def get_lesson_type_display(self, language='ru'):
        """Получить отображаемое название типа занятия"""
        types = {
            'lecture': {'ru': 'Лекция', 'kz': 'Дәріс', 'en': 'Lecture'},
            'practice': {'ru': 'Практика', 'kz': 'Практика', 'en': 'Practice'},
            'lab': {'ru': 'Лабораторная', 'kz': 'Зертхана', 'en': 'Laboratory'},
            'exam': {'ru': 'Экзамен', 'kz': 'Емтихан', 'en': 'Exam'},
            'consultation': {'ru': 'Консультация', 'kz': 'Кеңес', 'en': 'Consultation'}
        }
        return types.get(self.schedule_type, {}).get(language, self.schedule_type)
    
    def to_dict(self, language='ru'):
        """Преобразовать в словарь для API"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'subject_name': self.title,
            'subject_code': self.course_code,
            'teacher_name': self.instructor,
            'classroom': self.room,
            'lesson_type': self.schedule_type,
            'lesson_type_display': self.get_lesson_type_display(language),
            'notes': self.description,
            'is_cancelled': self.is_cancelled,
            'cancellation_reason': self.cancellation_reason,
            'duration_minutes': self.duration_minutes,
            'group_name': self.group_name,
            'faculty': self.faculty,
            'location': self.location
        }
    
    def __repr__(self):
        return f'<Schedule {self.group_name}: {self.title} at {self.start_time}>'
