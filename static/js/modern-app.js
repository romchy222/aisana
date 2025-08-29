// Modern BolashakChat JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeAnimations();
    initializeChat();
    initializeLanguageSelector();
    loadChatHistory();
});

// Theme Management
function initializeTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const currentTheme = localStorage.getItem('theme') || 'light';

    // Set initial theme
    document.body.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const newTheme = document.body.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    }
}

// Animations
function initializeAnimations() {
    // Intersection Observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in-up');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    // Observe all feature cards and agent cards
    const animatedElements = document.querySelectorAll('.feature-card, .agent-card, .hero-content');
    animatedElements.forEach(el => observer.observe(el));
}

// Chat Functionality
function initializeChat() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-button');

    if (chatForm) {
        chatForm.addEventListener('submit', handleChatSubmit);
    }

    if (voiceButton) {
        voiceButton.addEventListener('click', handleVoiceInput);
    }

    // Auto-resize textarea
    if (chatInput) {
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    }
}

async function handleChatSubmit(e) {
    e.preventDefault();

    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');

    const message = chatInput.value.trim();
    if (!message) return;

    // Disable input and show loading
    chatInput.disabled = true;
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>';

    // Add user message to chat
    addMessageToChat('user', message);

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    const currentLanguage = getCurrentLanguage(); // Get current language
    let selectedAgent = window.selectedAgent; // Get selected agent

    try {
        // Отправляем запрос с явным указанием выбранного агента
        const requestData = {
            message: message,
            language: currentLanguage
        };

        // Добавляем агента только если он явно выбран
        if (selectedAgent && selectedAgent !== 'auto') {
            requestData.agent = selectedAgent;
            console.log(`Отправляем сообщение с принудительным выбором агента: ${selectedAgent}`);
        } else {
            requestData.agent = 'auto';
            console.log('Отправляем сообщение с автоматическим выбором агента');
        }

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (data.success) {
            console.log('Chat response data:', data);
            console.log('Message ID from response:', data.message_id);
            console.log('Detected language:', data.detected_language);
            // Add bot response to chat with feedback data
            addMessageToChat('bot', data.response, data.agent_name, data);

            // Check if the user's message was about schedule and open panel
            if (window.detectScheduleRequest && window.detectScheduleRequest(message)) {
                setTimeout(() => {
                    if (window.openSchedulePanel) {
                        window.openSchedulePanel();
                    }
                }, 1000); // Small delay to let the chat response appear first
            }
        } else {
            addMessageToChat('bot', 'Извините, произошла ошибка. Попробуйте еще раз.');
        }

    } catch (error) {
        console.error('Chat error:', error);
        addMessageToChat('bot', 'Ошибка соединения. Проверьте подключение к интернету.');
    }

    // Re-enable input
    chatInput.disabled = false;
    sendButton.disabled = false;
    sendButton.innerHTML = '<i class="fas fa-paper-plane me-1"></i>';
    chatInput.focus();
}

function addMessageToChat(sender, message, agentName = null, responseData = null) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;

    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

    const content = document.createElement('div');
    content.className = 'message-content';

    if (sender === 'bot' && agentName) {
        const agentLabel = document.createElement('div');
        agentLabel.className = 'message-meta';
        let languageFlag = '';
        if (responseData && responseData.detected_language) {
            const langFlags = {'ru': '🇷🇺', 'kz': '🇰🇿', 'en': '🇺🇸'};
            languageFlag = langFlags[responseData.detected_language] || '';
        }
        agentLabel.innerHTML = `<i class="fas fa-shield-check"></i> ${agentName} ${languageFlag}`;
        content.appendChild(agentLabel);
    }

    const messageText = document.createElement('div');
    messageText.className = 'message-bubble';

    // Process markdown for bot messages if marked.js is available
    if (sender === 'bot' && typeof marked !== 'undefined') {
        messageText.innerHTML = marked.parse(message);
    } else {
        // Fallback: simple text formatting
        messageText.innerHTML = message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    content.appendChild(messageText);

    // Добавляем кнопки лайк/дизлайк для ответов бота
    if (sender === 'bot' && responseData && responseData.message_id) {
        console.log('✅ Adding feedback buttons for message_id:', responseData.message_id);

        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'message-feedback';

        const likeBtn = document.createElement('button');
        likeBtn.className = 'feedback-btn like';
        likeBtn.innerHTML = '<i class="fas fa-thumbs-up"></i>';
        likeBtn.title = 'Полезно';
        likeBtn.onclick = () => sendFeedback(responseData.message_id, 'like', likeBtn, dislikeBtn);

        const dislikeBtn = document.createElement('button');
        dislikeBtn.className = 'feedback-btn dislike';
        dislikeBtn.innerHTML = '<i class="fas fa-thumbs-down"></i>';
        dislikeBtn.title = 'Не полезно';
        dislikeBtn.onclick = () => sendFeedback(responseData.message_id, 'dislike', dislikeBtn, likeBtn);

        const feedbackMessage = document.createElement('span');
        feedbackMessage.className = 'feedback-message';

        feedbackDiv.appendChild(likeBtn);
        feedbackDiv.appendChild(dislikeBtn);
        feedbackDiv.appendChild(feedbackMessage);

        content.appendChild(feedbackDiv);
    } else if (sender === 'bot') {
        console.log('❌ No feedback buttons added - responseData:', responseData);
        console.log('❌ Sender:', sender, 'Has responseData:', !!responseData, 'Has message_id:', responseData && responseData.message_id);
    }

    messageElement.appendChild(avatar);
    messageElement.appendChild(content);

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Функция отправки обратной связи
async function sendFeedback(messageId, feedbackType, activeBtn, otherBtn) {
    try {
        // Отключаем кнопки во время отправки
        activeBtn.disabled = true;
        otherBtn.disabled = true;

        // Показываем индикатор загрузки
        const originalIcon = activeBtn.innerHTML;
        activeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        const response = await fetch('/api/feedback/like-dislike', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_id: messageId,
                is_like: feedbackType === 'like'
            })
        });

        const data = await response.json();

        if (data.success) {
            // Активируем выбранную кнопку
            activeBtn.classList.add('active');
            otherBtn.classList.remove('active');

            // Показываем сообщение благодарности
            const feedbackMessage = activeBtn.parentNode.querySelector('.feedback-message');
            feedbackMessage.textContent = data.message || 'Спасибо за обратную связь!';
            feedbackMessage.classList.add('show');

            // Скрываем сообщение через 3 секунды
            setTimeout(() => {
                feedbackMessage.classList.remove('show');
            }, 3000);

        } else {
            console.error('Failed to send feedback:', data.error);
        }

        // Восстанавливаем иконку
        activeBtn.innerHTML = originalIcon;

    } catch (error) {
        console.error('Error sending feedback:', error);
        // Восстанавливаем иконку при ошибке
        activeBtn.innerHTML = originalIcon;
    } finally {
        // Включаем кнопки обратно
        activeBtn.disabled = false;
        otherBtn.disabled = false;
    }
}

// Voice Input
function handleVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Голосовой ввод не поддерживается в вашем браузере');
        return;
    }

    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    const voiceButton = document.getElementById('voice-button');
    const chatInput = document.getElementById('chat-input');

    recognition.lang = getCurrentLanguage() === 'kz' ? 'kk-KZ' : 'ru-RU';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function() {
        voiceButton.innerHTML = '<i class="fas fa-microphone-slash text-danger"></i>';
        voiceButton.classList.add('recording');
    };

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        chatInput.focus();
    };

    recognition.onend = function() {
        voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceButton.classList.remove('recording');
    };

    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceButton.classList.remove('recording');
    };

    recognition.start();
}

// Language Management
function initializeLanguageSelector() {
    const languageLinks = document.querySelectorAll('[href*="lang="]');
    languageLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Close modal if open
            const modal = bootstrap.Modal.getInstance(document.getElementById('languageModal'));
            if (modal) {
                modal.hide();
            }
        });
    });
}

function getCurrentLanguage() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('lang') || 'ru';
}

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function formatDateTime(dateString) {
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString(getCurrentLanguage(), options);
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Loading states for buttons
function setButtonLoading(button, loading = true) {
    if (!button) return;

    if (loading) {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.setAttribute('data-original-text', originalText);
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Загрузка...';
    } else {
        button.disabled = false;
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
        }
    }
}

// Form validation helpers
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Chat History Management
function displayMessage(message, sender, language, agentName = null) {
    // Wrapper function for addMessageToChat to support history loading
    addMessageToChat(sender, message, agentName);
}

function loadChatHistory() {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;

    fetch('/api/chat/history')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.history && data.history.length > 0) {
                chatMessages.innerHTML = ''; // Clear existing messages
                data.history.forEach(item => {
                    displayMessage(item.message, 'user', item.language);
                    displayMessage(item.response, 'bot', item.language, item.agent_name);
                });
                scrollChatToBottom();
            }
        })
        .catch(error => {
            console.log('Chat history not available:', error);
        });
}

function clearChatHistory() {
    if (confirm(getClearHistoryText())) {
        fetch('/api/chat/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const chatMessages = document.getElementById('chat-messages');
                if (chatMessages) {
                    chatMessages.innerHTML = '<div class="welcome-message">' + getWelcomeMessage() + '</div>';
                }
                showToast(getClearSuccessText(), 'success');
            }
        })
        .catch(error => {
            console.error('Error clearing history:', error);
            showToast('Ошибка при очистке истории', 'error');
        });
    }
}

function getClearHistoryText() {
    const currentLang = getCurrentLanguage();
    const texts = {
        'ru': 'Вы уверены, что хотите очистить историю чата?',
        'kz': 'Чат тарихын тазалағыңыз келетініне сенімдісіз бе?',
        'en': 'Are you sure you want to clear chat history?'
    };
    return texts[currentLang] || texts['ru'];
}

function getClearSuccessText() {
    const currentLang = getCurrentLanguage();
    const texts = {
        'ru': 'История чата очищена',
        'kz': 'Чат тарихы тазаланды',
        'en': 'Chat history cleared'
    };
    return texts[currentLang] || texts['ru'];
}

function getWelcomeMessage() {
    const currentLang = getCurrentLanguage();
    const texts = {
        'ru': 'Добро пожаловать! Задайте свой вопрос университетскому AI-помощнику.',
        'kz': 'Қош келдіңіз! Университеттің AI-көмекшісіне сұрағыңызды қойыңыз.',
        'en': 'Welcome! Ask your question to the university AI assistant.'
    };
    return texts[currentLang] || texts['ru'];
}

// --- New functions for agent selection ---

// Функция для отправки сообщения с указанным агентом
window.startChatWithAgent = function(agentType) {
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        // Устанавливаем выбранного агента
        window.selectedAgent = agentType;

        // Показываем уведомление о выбранном агенте
        showAgentSelection(agentType);

        // Добавляем визуальную индикацию выбранного агента
        updateAgentIndicator(agentType);

        // Фокус на поле ввода
        const messageInput = document.getElementById('user-message');
        if (messageInput) {
            messageInput.focus();
            messageInput.placeholder = `Задайте вопрос агенту ${getAgentDisplayName(agentType)}...`;
        }
    }
};

// Функция для обновления индикатора выбранного агента
function updateAgentIndicator(agentType) {
    let indicator = document.getElementById('selected-agent-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'selected-agent-indicator';
        indicator.className = 'selected-agent-indicator';

        const chatHeader = document.querySelector('.chat-header');
        if (chatHeader) {
            chatHeader.appendChild(indicator);
        }
    }

    const agentName = getAgentDisplayName(agentType);
    indicator.innerHTML = `
        <div class="agent-badge">
            <i class="fas fa-robot"></i>
            <span>Выбран: ${agentName}</span>
            <button onclick="clearAgentSelection()" class="clear-agent-btn" title="Сбросить выбор агента">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    indicator.style.display = 'block';
}

// Функция для сброса выбора агента
window.clearAgentSelection = function() {
    window.selectedAgent = null;

    const indicator = document.getElementById('selected-agent-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }

    const messageInput = document.getElementById('user-message');
    if (messageInput) {
        messageInput.placeholder = 'Задайте ваш вопрос...';
    }
};

// Функция для получения отображаемого имени агента
function getAgentDisplayName(agentType) {
    const agentNames = {
        'ai_abitur': 'AI-Abitur (Поступление)',
        'kadrai': 'KadrAI (HR вопросы)',
        'uninav': 'UniNav (Студенческие вопросы)',
        'career_navigator': 'CareerNavigator (Карьера)',
        'uniroom': 'UniRoom (Общежитие)'
    };
    return agentNames[agentType] || agentType;
}

// Placeholder for showAgentSelection if it's defined elsewhere
function showAgentSelection(agentType) {
    console.log(`Agent selected: ${agentType}`);
    // Implement actual UI update if needed
}

// Placeholder for scrollChatToBottom if it's defined elsewhere
function scrollChatToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Placeholder for showToast if it's defined elsewhere
function showToast(message, type) {
    console.log(`Toast (${type}): ${message}`);
    // Implement actual toast notification logic
}
// --- End of new functions ---

function getCurrentLanguage() {
    // Get language from URL parameter or default to 'ru'
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('lang') || 'ru';
}

// Export functions for global use
window.BolashakChat = {
    showNotification,
    setButtonLoading,
    validateForm,
    getCurrentLanguage,
    formatDateTime,
    loadChatHistory,
    clearChatHistory,
    startChatWithAgent, // Exporting new function
    clearAgentSelection // Exporting new function
};