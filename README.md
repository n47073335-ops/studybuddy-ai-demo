# StudyBuddy AI Demo

A Vietnamese personal learning assistant prototype combining a relational SQLite database, retrieval-augmented generation (RAG), and optional Gemini LLM generation.

**Windows:** run `run_demo.bat`. **macOS/Linux:** run `./run_demo.sh`. Open `http://127.0.0.1:8000`.

Without an API key, the backend still supports SQLite and keyword-based retrieval, but not LLM generation. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` on the server to enable real Gemini responses. Never expose the API key or share `.env`.

See [HUONG_DAN_VA_TRINH_BAY.md](HUONG_DAN_VA_TRINH_BAY.md) for detailed Vietnamese setup and presentation steps.
