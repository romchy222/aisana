// Schedule Panel JavaScript
class SchedulePanel {
    constructor() {
        this.currentGroup = null;
        this.currentTab = 'today';
        this.init();
    }

    init() {
        this.loadGroups();
        // Initialize with today's tab active
        this.switchTab('today');
    }

    // Load available groups
    async loadGroups() {
        try {
            const response = await fetch('/api/schedule/groups');
            const data = await response.json();
            
            const select = document.getElementById('group-select');
            select.innerHTML = '<option value="">Выберите группу</option>';
            
            if (data.success && data.groups) {
                data.groups.forEach(group => {
                    const option = document.createElement('option');
                    option.value = group.name;
                    option.textContent = `${group.name} (${group.faculty.name})`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading groups:', error);
            const select = document.getElementById('group-select');
            select.innerHTML = '<option value="">Ошибка загрузки групп</option>';
        }
    }

    // Switch between tabs
    switchTab(tabName) {
        this.currentTab = tabName;
        
        // Update tab buttons
        const tabs = document.querySelectorAll('.schedule-tab');
        tabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            }
        });

        // Update tab content visibility
        const contents = document.querySelectorAll('.schedule-tab-content');
        contents.forEach(content => {
            content.style.display = 'none';
        });
        
        const activeContent = document.getElementById(`schedule-${tabName}`);
        if (activeContent) {
            activeContent.style.display = 'block';
        }

        // Load data for current group if selected
        if (this.currentGroup) {
            this.loadScheduleData(tabName, this.currentGroup);
        }
    }

    // Load schedule for selected group
    async loadScheduleForGroup() {
        const select = document.getElementById('group-select');
        const groupName = select.value;
        
        if (!groupName) {
            this.showEmptyState('Выберите группу для просмотра расписания');
            return;
        }

        this.currentGroup = groupName;
        await this.loadScheduleData(this.currentTab, groupName);
    }

    // Load schedule data from API
    async loadScheduleData(period, groupName) {
        const contentId = `schedule-${period}`;
        const container = document.getElementById(contentId);
        
        if (!container) return;

        // Show loading state
        container.innerHTML = `
            <div class="schedule-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Загрузка расписания...</p>
            </div>
        `;

        try {
            let endpoint = '';
            switch (period) {
                case 'today':
                    endpoint = `/api/schedule/today/${encodeURIComponent(groupName)}`;
                    break;
                case 'tomorrow':
                    endpoint = `/api/schedule/tomorrow/${encodeURIComponent(groupName)}`;
                    break;
                case 'week':
                    endpoint = `/api/schedule/week/${encodeURIComponent(groupName)}`;
                    break;
                default:
                    throw new Error('Unknown period');
            }

            const response = await fetch(endpoint);
            const data = await response.json();

            if (data.success) {
                if (period === 'week') {
                    this.renderWeekSchedule(container, data.schedule_by_days, data.group);
                } else {
                    this.renderDaySchedule(container, data.schedules, data.group, data.date);
                }
            } else {
                this.showError(container, data.error || 'Ошибка загрузки расписания');
            }
        } catch (error) {
            console.error('Error loading schedule:', error);
            this.showError(container, 'Ошибка соединения с сервером');
        }
    }

    // Render daily schedule
    renderDaySchedule(container, schedules, groupName, date) {
        if (!schedules || schedules.length === 0) {
            container.innerHTML = `
                <div class="schedule-empty">
                    <i class="fas fa-calendar-times"></i>
                    <h6>Занятий нет</h6>
                    <p>На этот день не запланировано занятий для группы ${groupName}</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="schedule-date-header">
                <h6 style="color: var(--chat-text); margin-bottom: 1rem;">
                    <i class="fas fa-calendar"></i>
                    ${this.formatDate(date)} - ${groupName}
                </h6>
            </div>
        `;

        schedules.forEach(lesson => {
            html += this.renderScheduleItem(lesson);
        });

        container.innerHTML = html;
    }

    // Render weekly schedule
    renderWeekSchedule(container, scheduleByDays, groupName) {
        if (!scheduleByDays || Object.keys(scheduleByDays).length === 0) {
            container.innerHTML = `
                <div class="schedule-empty">
                    <i class="fas fa-calendar-times"></i>
                    <h6>Занятий нет</h6>
                    <p>На эту неделю не запланировано занятий для группы ${groupName}</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="schedule-week-header">
                <h6 style="color: var(--chat-text); margin-bottom: 1rem;">
                    <i class="fas fa-calendar-week"></i>
                    Расписание на неделю - ${groupName}
                </h6>
            </div>
        `;

        // Sort dates
        const sortedDates = Object.keys(scheduleByDays).sort();
        
        sortedDates.forEach(date => {
            const lessons = scheduleByDays[date];
            html += `
                <div class="schedule-day-section" style="margin-bottom: 1.5rem;">
                    <h6 style="color: var(--chat-primary); font-weight: 600; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--chat-border);">
                        ${this.formatDate(date)}
                    </h6>
            `;
            
            lessons.forEach(lesson => {
                html += this.renderScheduleItem(lesson);
            });
            
            html += '</div>';
        });

        container.innerHTML = html;
    }

    // Render individual schedule item
    renderScheduleItem(lesson) {
        const typeColors = {
            'lecture': 'var(--chat-primary)',
            'practice': '#f59e0b',
            'lab': '#10b981',
            'exam': '#ef4444',
            'consultation': '#8b5cf6'
        };

        const typeColor = typeColors[lesson.lesson_type] || 'var(--chat-primary)';

        return `
            <div class="schedule-item">
                <div class="schedule-item-time">
                    <i class="fas fa-clock"></i>
                    ${lesson.start_time} - ${lesson.end_time}
                    <span class="schedule-badge" style="background: ${typeColor};">
                        ${lesson.lesson_type_display}
                    </span>
                </div>
                <div class="schedule-item-subject">${lesson.subject_name}</div>
                <div class="schedule-item-details">
                    <div class="schedule-item-teacher">
                        <i class="fas fa-chalkboard-teacher"></i>
                        ${lesson.teacher_name}
                    </div>
                    <div class="schedule-item-room">
                        <i class="fas fa-door-open"></i>
                        Аудитория ${lesson.classroom}
                    </div>
                    ${lesson.notes ? `
                        <div class="schedule-item-notes">
                            <i class="fas fa-sticky-note"></i>
                            ${lesson.notes}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    // Show error state
    showError(container, message) {
        container.innerHTML = `
            <div class="schedule-empty">
                <i class="fas fa-exclamation-triangle" style="color: #ef4444;"></i>
                <h6 style="color: #ef4444;">Ошибка</h6>
                <p>${message}</p>
            </div>
        `;
    }

    // Show empty state
    showEmptyState(message) {
        const contents = document.querySelectorAll('.schedule-tab-content');
        contents.forEach(content => {
            content.innerHTML = `
                <div class="schedule-loading">
                    <i class="fas fa-calendar-alt"></i>
                    <p>${message}</p>
                </div>
            `;
        });
    }

    // Format date for display
    formatDate(dateStr) {
        const date = new Date(dateStr);
        const days = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
        const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
        
        const dayName = days[date.getDay()];
        const day = date.getDate();
        const month = months[date.getMonth()];
        
        return `${dayName}, ${day} ${month}`;
    }

    // Open schedule panel
    show() {
        const panel = document.getElementById('schedule-panel');
        if (panel) {
            panel.classList.add('active');
        }
    }

    // Close schedule panel
    hide() {
        const panel = document.getElementById('schedule-panel');
        if (panel) {
            panel.classList.remove('active');
        }
    }
}

// Global instance
let schedulePanel = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('schedule-panel')) {
        schedulePanel = new SchedulePanel();
    }
});

// Global functions for inline event handlers
function switchScheduleTab(tabName) {
    if (schedulePanel) {
        schedulePanel.switchTab(tabName);
    }
}

function loadScheduleForGroup() {
    if (schedulePanel) {
        schedulePanel.loadScheduleForGroup();
    }
}

function closeSchedulePanel() {
    if (schedulePanel) {
        schedulePanel.hide();
    }
}

function openSchedulePanel() {
    if (schedulePanel) {
        schedulePanel.show();
    }
}

// Function to detect schedule-related messages
function detectScheduleRequest(message) {
    const scheduleKeywords = [
        'расписание', 'занятия', 'пары', 'лекции', 'семинары',
        'schedule', 'classes', 'lessons', 'lectures',
        'сегодня', 'завтра', 'на неделю', 'today', 'tomorrow', 'week',
        'когда пары', 'какие занятия', 'время занятий'
    ];
    
    const lowerMessage = message.toLowerCase();
    return scheduleKeywords.some(keyword => lowerMessage.includes(keyword));
}

// Export for global access
window.SchedulePanel = SchedulePanel;
window.detectScheduleRequest = detectScheduleRequest;
window.openSchedulePanel = openSchedulePanel;