import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
import requests
import json

from utils.logger import setup_logger
logger = setup_logger(__name__)

class LLMManager:
    """Modular LLM manager with fallback mechanism"""
    
    def __init__(self):
        self.providers = ["nvidia", "google", "openrouter"]
        self.current_provider_idx = 0
        
    def _try_nvidia(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Try NVIDIA NIM API"""
        try:
            from config.settings import NIM_API_KEY, NIM_MODEL
            
            if not NIM_API_KEY:
                raise ValueError("NVIDIA API key not configured")
            
            headers = {
                "Authorization": f"Bearer {NIM_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": NIM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"NVIDIA API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"NVIDIA API failed: {e}")
            return None
    
    def _try_google(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Try Google Gemini API"""
        try:
            from config.settings import GOOGLE_API_KEY, GOOGLE_MODEL
            
            if not GOOGLE_API_KEY:
                raise ValueError("Google API key not configured")
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(GOOGLE_MODEL)
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Google Gemini failed: {e}")
            return None
    
    def _try_openrouter(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Try OpenRouter API"""
        try:
            from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL
            
            if not OPENROUTER_API_KEY:
                raise ValueError("OpenRouter API key not configured")
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "GitHub AI Agent"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"OpenRouter failed: {e}")
            return None
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text with fallback mechanism
        Returns: Generated text or empty string if all providers fail
        """
        # Start with configured provider
        start_idx = 0
        providers = ["nvidia", "google", "openrouter"]
        
        for i in range(len(providers)):
            provider_idx = (start_idx + i) % len(providers)
            provider = providers[provider_idx]
            
            logger.info(f"Trying {provider} provider...")
            
            result = None
            if provider == "nvidia":
                result = self._try_nvidia(prompt, system_prompt)
            elif provider == "google":
                result = self._try_google(prompt, system_prompt)
            elif provider == "openrouter":
                result = self._try_openrouter(prompt, system_prompt)
            
            if result:
                logger.info(f"Successfully generated text using {provider}")
                return result
        
        logger.error("All LLM providers failed")
        return ""
    
    def test_connection(self) -> Dict[str, bool]:
        """Test connection to all providers"""
        test_prompt = "Hello, are you working?"
        
        results = {}
        for provider in self.providers:
            try:
                if provider == "nvidia":
                    result = self._try_nvidia(test_prompt)
                elif provider == "google":
                    result = self._try_google(test_prompt)
                elif provider == "openrouter":
                    result = self._try_openrouter(test_prompt)
                
                results[provider] = bool(result)
                # Use ASCII characters instead of Unicode for Windows compatibility
                status = "OK" if results[provider] else "FAIL"
                logger.info(f"{provider}: {status}")
            except Exception as e:
                results[provider] = False
                logger.error(f"{provider} test failed: {e}")
        
        return results