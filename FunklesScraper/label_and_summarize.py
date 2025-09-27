# label_and_summarize.py
from paths import ENV_PATH

class Labeler:
    def __init__(self, env_path=ENV_PATH, cache_dir="filings_cache", label_file="labels.txt"):
        from dotenv import load_dotenv
        from google import genai
        import os, time, json

        self.cache_dir = cache_dir
        self.label_file = label_file

        # Load API key
        load_dotenv(env_path)
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
        if os.path.exists(label_file):
            with open(label_file, "r") as f:
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
        prompt = f"...same as before..."
        response = self.safe_generate(self.gemini.models.generate_content, model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()

    def generate_summary(self, text):
        prompt = f"...same as before..."
        response = self.safe_generate(self.gemini.models.generate_content, model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()

    def label_and_summarize_filings(self):
        import os, json
        for root, dirs, files in os.walk(self.cache_dir):
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
