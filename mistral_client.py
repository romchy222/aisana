import os
import logging
import requests

logger = logging.getLogger(__name__)


class MistralClient:
    """Client for interacting with OpenRouter API"""

    def __init__(self):
        # Ключ берём из окружения
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not found in environment variables")

        self.base_url = "https://openrouter.ai/api/v1"
        # Используем рабочую бесплатную модель
        self.model = "microsoft/phi-3-mini-128k-instruct:free"
        self.free_models = [
            "microsoft/phi-3-mini-128k-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "google/gemini-pro:free",
            "openai/gpt-3.5-turbo:free"
        ]

        self.system_prompts = {
            'ru': """
        Ты — AI-ассистент для абитуриентов и студентов Кызылординского университета "Болашак". Отвечай кратко, дружелюбно и информативно на русском языке. Используй следующие возможности:
        - Помогаешь поступающим по вопросам приёмной кампании, документов, сроков, образовательных программ, стоимости, проживания, стипендий, расписания, трудоустройства и другим вопросам.
        - Даёшь справочную информацию о цифровых сервисах университета: AI-бот, Студенческий навигатор, GreenNavigator, бот по вопросам общежития.
        - Помогаешь найти контакты, расписания, условия поступления, шаги для подачи документов, возможности трудоустройства и проживания, способы обращения за консультацией.
        - В случае отсутствия информации — советуй обратиться в приёмную комиссию или соответствующие службы.
        - Всегда отвечай в формате Markdown.
        """,
            'kz': """
        Сіз Қызылорда "Болашақ" университетінің талапкерлері мен студенттеріне арналған AI-ассистентсіз. Қазақ тілінде қысқа, достық және ақпараттық жауап беріңіз. Мына бағыттарда көмектесесіз:
        - Қабылдау науқаны, құжаттар, мерзімдер, білім бағдарламалары, оқу ақысы, жатақхана, стипендия, сабақ кестесі, жұмысқа орналасу және басқа да сұрақтарға жауап бересіз.
        - Университеттің цифрлық сервистері туралы ақпарат бересіз: AI-бот, Студенттік навигатор, GreenNavigator, жатақхана бойынша бот.
        - Байланыс деректерін, қабылдау талаптарын, құжат тапсыру қадамдарын, жұмысқа орналасу және тұру мүмкіндіктерін, кеңес алу жолдарын түсіндіресіз.
        - Жауаптарды тек Markdown форматында беріңіз.
        """
        }

    def get_response(self, user_message: str, context: str = "", language: str = "ru") -> str:
        try:
            if not self.api_key:
                logger.error("OpenRouter API key not configured")
                return self._get_fallback_response(language)

            system_prompt = self.system_prompts.get(language, self.system_prompts['ru'])

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос пользователя: {user_message}"}
            ]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bolashak-chat.replit.app",
                "X-Title": "Bolashak University AI Chat"
            }

            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }

            response = requests.post(f"{self.base_url}/chat/completions",
                                     headers=headers,
                                     json=data,
                                     timeout=30)

            # Если модель недоступна, пробуем другие бесплатные модели
            if response.status_code == 404 and self.model in self.free_models:
                current_index = self.free_models.index(self.model)
                for backup_model in self.free_models[current_index + 1:]:
                    logger.info(f"Trying backup model: {backup_model}")
                    data["model"] = backup_model
                    backup_response = requests.post(f"{self.base_url}/chat/completions",
                                                   headers=headers,
                                                   json=data,
                                                   timeout=30)
                    if backup_response.status_code == 200:
                        self.model = backup_model  # Обновляем на рабочую модель
                        logger.info(f"Switched to working model: {backup_model}")
                        response = backup_response
                        break

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()
                else:
                    logger.error("No choices in OpenRouter response")
                    return self._get_fallback_response(language)
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return self._get_fallback_response(language)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to OpenRouter API: {str(e)}")
            return self._get_fallback_response(language)
        except Exception as e:
            logger.error(f"Unexpected error in OpenRouter client: {str(e)}")
            return self._get_fallback_response(language)

    def get_response_with_system_prompt(self,
                                        user_message: str,
                                        context: str = "",
                                        language: str = "ru",
                                        custom_system_prompt: str = "") -> str:
        """Get response using enhanced prompt engineering and custom system prompt"""
        try:
            if not self.api_key:
                logger.error("OpenRouter API key not configured")
                return self._get_fallback_response(language)

            system_prompt = custom_system_prompt if custom_system_prompt else self.system_prompts.get(language, self.system_prompts['ru'])

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос пользователя: {user_message}"}
            ]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bolashak-chat.replit.app",
                "X-Title": "Bolashak University AI Chat"
            }

            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }

            response = requests.post(f"{self.base_url}/chat/completions",
                                     headers=headers,
                                     json=data,
                                     timeout=30)

            # Если модель недоступна, пробуем другие бесплатные модели
            if response.status_code == 404 and self.model in self.free_models:
                current_index = self.free_models.index(self.model)
                for backup_model in self.free_models[current_index + 1:]:
                    logger.info(f"Trying backup model in enhanced method: {backup_model}")
                    data["model"] = backup_model
                    backup_response = requests.post(f"{self.base_url}/chat/completions",
                                                   headers=headers,
                                                   json=data,
                                                   timeout=30)
                    if backup_response.status_code == 200:
                        self.model = backup_model  # Обновляем на рабочую модель
                        logger.info(f"Switched to working model in enhanced method: {backup_model}")
                        response = backup_response
                        break

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()
                else:
                    logger.error("No choices in OpenRouter response")
                    return self._get_fallback_response(language)
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return self._get_fallback_response(language)

        except Exception as e:
            logger.error(f"Unexpected error in enhanced OpenRouter client: {str(e)}")
            return self._get_fallback_response(language)

    def _get_fallback_response(self, language: str = "ru") -> str:
        fallback_responses = {
            'ru': "**Извините, я временно недоступен.**\n\nПожалуйста, обратитесь в приёмную комиссию университета по телефону или электронной почте.",
            'kz': "**Кешіріңіз, мен уақытша қолжетімсізбін.**\n\nУниверситеттің қабылдау комиссиясына телефон немесе электрондық пошта арқылы хабарласыңыз."
        }
        return fallback_responses.get(language, fallback_responses['ru'])

    def get_available_models(self):
        """Get list of available models from OpenRouter"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(f"{self.base_url}/models", headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get models: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return None

    def set_model(self, model_name: str):
        """Change the model being used"""
        self.model = model_name
        logger.info(f"Switched to model: {model_name}")