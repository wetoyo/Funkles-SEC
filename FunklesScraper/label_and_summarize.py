# label_and_summarize.py
from .paths import ENV_PATH, CACHE_DIR, LABEL_PATH

class Labeler:
    def __init__(self):
        
        from dotenv import load_dotenv
        from google import genai
        import os, time, json
        

        # Load API key
        load_dotenv(ENV_PATH)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key is None:
            raise ValueError("GEMINI_API_KEY not found in .env")

        self.gemini = genai.Client(api_key=self.api_key)

        # Rate limiting
        self.max_rpm = 5
        self.max_tpm = 100_000
        self.request_interval = 60 / self.max_rpm
        self.last_request_time = 0
        self.tokens_used = 0
        self.tpm_reset_time = time.time() + 60

        # Load labels
        if os.path.exists(LABEL_PATH):
            with open(LABEL_PATH, "r") as f:
                self.labels = set(f.read().splitlines())
        else:
            self.labels = set()

    def safe_generate(self, func, *args, **kwargs):
        import time
        while True:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.request_interval:
                time.sleep(self.request_interval - elapsed)

            if time.time() > self.tpm_reset_time:
                self.tokens_used = 0
                self.tpm_reset_time = time.time() + 60

            try:
                response = func(*args, **kwargs)
                self.tokens_used += len(response.text) // 4
                self.last_request_time = time.time()

                if self.tokens_used >= self.max_tpm:
                    time.sleep(self.tpm_reset_time - time.time())
                    self.tokens_used = 0
                    self.tpm_reset_time = time.time() + 60

                return response
            except Exception as e:
                if "429" in str(e):
                    time.sleep(10)
                    continue
                else:
                    raise

    def generate_label(self, text):
        prompt = f"""
            You are an expert at classifying SEC filings.

            Task:
            - Read the following filing text.
            - Assign it to one of the existing labels if it fits.
            - If none of the existing labels fit, suggest a concise new label.

            Filing text:
            {text}

            Existing labels:
            {', '.join(self.labels) if self.labels else 'None'}

            Instructions:
            - Return only the label, no extra explanation.
            - Keep the label short and descriptive.
            """
        response = self.safe_generate(self.gemini.models.generate_content, model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()

    def generate_summary(self, text):
        prompt = f"""
        You are an expert at summarizing SEC filings.

        Task:
        - Read the following filing text.
        - Write a concise summary highlighting the key points, such as ownership, transactions, or corporate actions.

        Filing text:
        {text}

        Instructions:
        - Keep the summary brief (2–4 sentences).
        - Focus on the most important facts.
        - Do not include personal opinions or extra commentary.
        """
        response = self.safe_generate(self.gemini.models.generate_content, model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()

    def run(self):
        import os, json
        for root, dirs, files in os.walk(CACHE_DIR):
            for file in files:
                if file.endswith(".meta.json"):
                    meta_path = os.path.join(root, file)
                    with open(meta_path, "r") as f:
                        meta = json.load(f)

                    with open(meta["path"], "r") as f:
                        content = f.read()

                    label = self.generate_label(content)
                    if label not in self.labels:
                        self.labels.add(label)
                        with open(self.label_file, "a") as f:
                            f.write(label + "\n")

                    meta["label"] = label
                    meta["summary"] = self.generate_summary(content)
                    with open(meta_path, "w") as f:
                        json.dump(meta, f, indent=4)
