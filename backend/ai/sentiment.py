import os
from ollama import AsyncClient

host_url = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11435')
client = AsyncClient(host=host_url)

class SentimentAnalyzer:
    def __init__(self, model_name: str = "qwen2:0.5b"):
        self.model_name = model_name

    async def analyze_sentiment(self, text: str) -> str:
        """
        Analyzes the sentiment of a text chunk.
        Returns: positive, neutral, or negative.
        """
        prompt = f"Analyze the emotional sentiment of the following meeting excerpt. Reply with ONLY ONE WORD: Positive, Neutral, or Negative.\n\nExcerpt: {text}"
        
        try:
            response = await client.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}])
            word = response['message']['content'].strip().lower()
            if "positive" in word:
                return "Positive"
            if "negative" in word:
                return "Negative"
            return "Neutral"
        except Exception as e:
            print(f"Ollama error: {e}")
            return "Neutral"
