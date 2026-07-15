import requests
from django.conf import settings


class OllamaClient:
    def __init__(self):
        self.url = getattr(settings, "OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = getattr(settings, "OLLAMA_MODEL", "llama3.2:3b")
        self.session = requests.Session()

    def generate(self, prompt, temperature=0.2, num_predict=120, timeout=20):
        response = self.session.post(
            self.url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict,
                    "num_ctx": 2048,
                },
            },
            timeout=timeout,
        )

        response.raise_for_status()
        return response.json().get("response", "").strip()