# BolashakChat - AI Agent System

## Overview
BolashakChat is a multilingual (Russian/Kazakh) university chatbot system for Bolashak University. It employs a multi-agent architecture with 5 specialized AI agents to handle various university processes and student needs. The system aims to be a comprehensive digital assistant for applicants, students, faculty, and staff, providing intelligent responses through advanced natural language processing and knowledge management. Its vision is to streamline university operations, improve communication, and enhance the overall experience for all stakeholders.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Multi-Agent Architecture
The system is built around a multi-agent design:
- **AgentRouter**: Central component for routing incoming messages to the most appropriate specialized agent based on intent classification.
- **Specialized Agents**:
    - **AI-Abitur**: Admissions and enrollment inquiries.
    - **KadrAI**: HR processes for faculty and staff.
    - **UniNav**: Academic guidance for current students.
    - **CareerNavigator**: Career guidance and job placement.
    - **UniRoom**: Dormitory services and accommodation.

### Web Framework and Backend
- **Flask Application**: Modular Flask application using blueprints for admin, authentication, and main views.
- **Database Architecture**: Flexible database configuration supporting SQLite, PostgreSQL, and MySQL via SQLAlchemy ORM, with Alembic-style migrations.
- **Knowledge Management**: Processes documents, websites, and structured data with semantic search, TF-IDF scoring, and content chunking.

### Advanced AI and Processing Systems
- **Intent Classification**: Machine learning-based intent classifier for routing messages with confidence scoring. Includes a self-learning ML Router that improves agent selection over time based on user interactions and feedback.
- **Semantic Search**: Enhanced search engine with embedding simulation, knowledge graphs, and relationship mapping.
- **Response Optimization**: Multi-layered caching system for frequently asked questions.
- **Analytics and Learning**: Tracks user behavior, satisfaction metrics, and enables continuous learning.
- **Personalization**: Builds user profiles, tracks preferences, and adapts response styles.
- **Automatic Language Detection**: Analyzes text to automatically detect and respond in Russian, Kazakh, or English.

### Document Processing and Content Management
- **Document Processor**: Handles various file types (PDF, DOC, HTML, TXT) for text extraction and indexing.
- **Localization System**: Full internationalization support with dynamic language switching for Russian, Kazakh, and English, including locale-specific content delivery.

### Frontend and User Interface
- **Modern Web Interface**: Responsive design using Bootstrap 5, custom CSS, and progressive web app capabilities, offering both a web chat and embeddable widget.
- **Real-time Features**: WebSocket-like functionality for live chat and real-time response streaming.
- **Feedback System**: User-friendly like/dislike feedback system integrated with the ML Router.
- **Enhanced Dark Theme**: Modern dark theme with blue-gray color palette (#0f1419, #1a2332, #334155) for better user experience and reduced eye strain.
- **Futuristic Admin UI**: Revolutionary admin panel design featuring particles.js background, glassmorphism cards, gradient animations, 3D transforms, and interactive hover effects creating a truly epic experience.

### Security and Administration
- **Role-based Authentication**: Secure admin panel with session management and access controls.
- **Epic Futuristic Admin Dashboard**: Revolutionary admin interface featuring particles.js animated background, glassmorphism effects with backdrop blur, gradient rainbow titles, 3D hover transformations on stat cards, shimmer button animations, interactive Chart.js visualizations, parallax scroll effects, and comprehensive theme support (dark/light). The dashboard provides real-time monitoring with mind-blowing visual design that looks like it's from the future.

### Feature Specifications
- **Chat History**: Session-based history tracking with persistent storage and management API. Complete implementation with UUID session management, automatic loading on page refresh, and full frontend-backend integration.
- **University Information Integration**: Agents reference the official university website and provide comprehensive contact information (phone, email, social media, address, public transport).
- **About Page**: Comprehensive multilingual "About Us" page with university information, AI assistant features, contact details, and navigation integration.

## External Dependencies

- **AI Service Integration**: Mistral AI API for natural language processing.
- **Database Systems**: PostgreSQL, MySQL, SQLite.
- **Python Libraries**: Flask ecosystem (Flask-SQLAlchemy, Flask-CORS), SQLAlchemy, Requests, Werkzeug, Trafilatura, PyPDF2, python-docx.
- **Frontend Dependencies**: Bootstrap 5, Font Awesome, Chart.js.
- **Development and Deployment**: GitHub Actions (CI/CD), Gunicorn, Docker.
- **Optional Integrations**: Redis.