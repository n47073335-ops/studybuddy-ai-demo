"""StudyBuddy AI demo backend: FastAPI + SQLite + RAG + optional Gemini API.
Use a server-side GEMINI_API_KEY; never put secrets in index.html.
"""
from __future__ import annotations
import json, os, re, sqlite3, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "studybuddy.db"
ENV_PATH = BASE_DIR / ".env"

def load_env_file() -> None:
    if not ENV_PATH.exists(): return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ: os.environ[key] = value
load_env_file()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
app = FastAPI(title="StudyBuddy AI API", version="1.0.0", description="Demo RAG + relational database + optional LLM")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL, subject TEXT NOT NULL DEFAULT 'Chưa phân loại', body TEXT NOT NULL,
 file_type TEXT NOT NULL DEFAULT 'Ghi chú', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS document_chunks (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 chunk_index INTEGER NOT NULL, chunk_text TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(document_id, chunk_index)
);
CREATE TABLE IF NOT EXISTS conversations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS message_sources (
 id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
 chunk_id TEXT NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE, score REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS study_tasks (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL, subject TEXT NOT NULL DEFAULT 'Chưa phân loại', due_date TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','done'))
);
CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
"""

def utcnow() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def normalize_tokens(text: str) -> list[str]:
    text = text.lower().replace("đ", "d")
    text = re.sub(r"[\u0300-\u036f]", "", __import__("unicodedata").normalize("NFD", text))
    return re.findall(r"[a-z0-9]+", text)

def chunk_text(text: str, max_chars: int = 850, overlap: int = 120) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            pieces.append(p)
        else:
            step = max_chars - overlap
            pieces.extend(p[i:i + max_chars] for i in range(0, len(p), step))
    return pieces or [text[:max_chars]]

def rebuild_chunks(conn: sqlite3.Connection, doc_id: str, body: str) -> None:
    conn.execute("DELETE FROM document_chunks WHERE document_id=?", (doc_id,))
    now = utcnow()
    for i, chunk in enumerate(chunk_text(body)):
        conn.execute("INSERT INTO document_chunks(id,document_id,chunk_index,chunk_text,created_at) VALUES(?,?,?,?,?)",
                     (f"{doc_id}-c{i}", doc_id, i, chunk, now))

def ensure_seed_data() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO users(id,full_name,email,created_at) VALUES(1,?,?,?)",
                     ("Sinh viên demo", "student@studybuddy.local", utcnow()))
        # Seed database on first run only.
        if conn.execute("SELECT COUNT(*) FROM documents WHERE user_id=1").fetchone()[0] == 0:
            seeds = [
             ("seed-rdb", "Nhập môn cơ sở dữ liệu quan hệ", "Cơ sở dữ liệu", "Tài liệu mẫu", "Cơ sở dữ liệu quan hệ tổ chức dữ liệu thành các bảng (quan hệ). Mỗi bảng gồm các hàng (bản ghi) và cột (thuộc tính). Khóa chính (Primary Key - PK) dùng để định danh duy nhất mỗi bản ghi; khóa ngoại (Foreign Key - FK) liên kết dữ liệu giữa các bảng và giúp duy trì toàn vẹn tham chiếu. Các thao tác phổ biến được thực hiện bằng SQL: SELECT để truy vấn, INSERT để thêm, UPDATE để sửa và DELETE để xóa. Chuẩn hóa dữ liệu giúp giảm dư thừa và hạn chế bất thường khi thêm, sửa, xóa. Trong hệ thống học tập, các bảng có thể gồm Users, Documents, DocumentChunks, Conversations, Messages và StudyTasks. Một người dùng có thể sở hữu nhiều tài liệu; mỗi tài liệu có thể được chia thành nhiều đoạn văn bản; một cuộc hội thoại chứa nhiều tin nhắn."),
             ("seed-rag", "RAG và mô hình ngôn ngữ lớn (LLM)", "Trí tuệ nhân tạo", "Tài liệu mẫu", "RAG là viết tắt của Retrieval-Augmented Generation, thường dịch là sinh tăng cường bằng truy xuất. Một quy trình RAG điển hình gồm: (1) nạp dữ liệu từ tài liệu; (2) chia nội dung thành các đoạn nhỏ (chunking); (3) lập chỉ mục hoặc tạo embedding; (4) khi người dùng đặt câu hỏi, truy xuất các đoạn có liên quan; (5) đưa câu hỏi cùng ngữ cảnh được truy xuất vào mô hình ngôn ngữ lớn (LLM); (6) sinh câu trả lời dựa trên ngữ cảnh và hiển thị nguồn. LLM là mô hình được huấn luyện trên lượng dữ liệu lớn để hiểu và tạo ngôn ngữ. RAG giúp câu trả lời bám sát kho kiến thức riêng, dễ bổ sung dữ liệu và có thể chỉ ra nguồn tham khảo, nhưng không bảo đảm loại bỏ hoàn toàn câu trả lời sai. Cần đánh giá chất lượng truy xuất, kiểm soát nội dung ngữ cảnh, bảo vệ dữ liệu cá nhân và cho người dùng kiểm tra nguồn."),
             ("seed-study", "Kỹ thuật học tập chủ động", "Phương pháp học", "Tài liệu mẫu", "Học tập chủ động là cách người học tự tham gia vào quá trình ghi nhớ và vận dụng kiến thức. Active recall (tự truy xuất) là thử nhớ câu trả lời trước khi xem lại tài liệu. Spaced repetition (ôn tập ngắt quãng) phân bổ việc ôn ra nhiều thời điểm thay vì học dồn. Interleaving là xen kẽ các dạng bài có liên quan để rèn khả năng nhận diện phương pháp. Sau mỗi buổi học, hãy viết tóm tắt bằng lời của mình, ghi lại điểm chưa hiểu và làm một số câu hỏi ngắn. Khi dùng trợ lý AI, nên yêu cầu giải thích từng bước, ví dụ mới và câu hỏi kiểm tra; không nên chỉ chép câu trả lời. Đối chiếu nội dung AI với giáo trình và nguồn được dẫn để hạn chế hiểu sai.")]
            for did, title, subject, file_type, body in seeds:
                now = utcnow()
                conn.execute("INSERT INTO documents(id,user_id,title,subject,body,file_type,created_at) VALUES(?,1,?,?,?,?,?)",
                             (did, title, subject, body, file_type, now))
                rebuild_chunks(conn, did, body)
        elif conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 0:
            for row in conn.execute("SELECT id,body FROM documents").fetchall(): rebuild_chunks(conn, row["id"], row["body"])
        if conn.execute("SELECT COUNT(*) FROM study_tasks WHERE user_id=1").fetchone()[0] == 0:
            for tid, title, subject, due in [
                ("task-1","Đọc lại khái niệm CSDL quan hệ","Cơ sở dữ liệu","Hôm nay"),
                ("task-2","Vẽ sơ đồ RAG và mô tả các bước","Trí tuệ nhân tạo","Ngày mai"),
                ("task-3","Tự kiểm tra 5 câu hỏi ôn tập","Ôn tập","Cuối tuần")]:
                conn.execute("INSERT INTO study_tasks(id,user_id,title,subject,due_date,status) VALUES(?,1,?,?,?,'todo')", (tid,title,subject,due))

ensure_seed_data()

class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    subject: str = Field(default="Chưa phân loại", max_length=120)
    body: str = Field(min_length=1, max_length=200000)
    file_type: str = Field(default="Ghi chú", max_length=40)

class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=5000)


def retrieve(question: str, top_k: int = 4) -> list[dict[str, Any]]:
    query_tokens = normalize_tokens(question)
    if not query_tokens: return []
    unique = set(query_tokens)
    with db() as conn:
        rows = conn.execute("""SELECT c.id AS chunk_id,c.document_id,c.chunk_index,c.chunk_text,d.title
          FROM document_chunks c JOIN documents d ON d.id=c.document_id WHERE d.user_id=1""").fetchall()
    corpus = [(r, normalize_tokens(r["chunk_text"])) for r in rows]
    doc_freq = {w: sum(1 for _, tokens in corpus if w in set(tokens)) for w in unique}
    results = []
    for row, tokens in corpus:
        token_set = set(tokens); score = 0.0
        for w in unique:
            tf = tokens.count(w)
            if tf: score += (1 + __import__('math').log(tf)) * (__import__('math').log(1 + (len(corpus)+1)/(doc_freq[w]+1)))
        if len(question.strip()) > 8 and question.strip().lower() in row["chunk_text"].lower(): score += 3
        score /= (1 + __import__('math').log(1 + len(tokens)/100))
        if score > 0.05:
            results.append({"id": row["chunk_id"], "document_id": row["document_id"], "title": row["title"], "text": row["chunk_text"], "score": round(score, 4)})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]

def gemini_generate(question: str, sources: list[dict[str, Any]]) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key: return None
    context = "\n\n".join(f"[Nguồn {i+1}: {s['title']}]\n{s['text']}" for i, s in enumerate(sources))
    prompt = f"""Bạn là StudyBuddy AI, trợ lý học tập bằng tiếng Việt. Trả lời rõ ràng, dễ hiểu và bám sát ngữ cảnh.
Quy tắc:
- Dùng ngữ cảnh bên dưới làm căn cứ chính; nếu tài liệu không chứa câu trả lời, hãy nói rõ phần nào chưa đủ dữ liệu.
- Không bịa nguồn, số liệu, hoặc trích dẫn.
- Có thể diễn giải và đưa ví dụ; chỉ ra giới hạn nếu cần.
- Cuối câu trả lời ghi mục 'Nguồn tham khảo' với tiêu đề nguồn đã dùng.

CÂU HỎI:
{question}

NGỮ CẢNH TRUY XUẤT:
{context if context else '[Không tìm thấy đoạn tài liệu phù hợp.]'}"""
    payload = json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":900}}, ensure_ascii=False).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json", "x-goog-api-key":api_key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return "\n".join(p.get("text","") for p in data.get("candidates", [{}])[0].get("content",{}).get("parts",[]) if p.get("text")) or None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:500]
        raise HTTPException(status_code=502, detail=f"Gemini API trả lỗi HTTP {e.code}. Kiểm tra khóa API/quyền truy cập/mô hình. {detail}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không gọi được Gemini API: {str(e)[:180]}")

def local_answer(question: str, sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "Mình chưa tìm thấy đoạn tài liệu đủ liên quan để trả lời chắc chắn. Hãy nạp thêm tài liệu hoặc đặt câu hỏi cụ thể hơn.\n\nĐây là chế độ RAG offline: truy xuất theo từ khóa đã chạy, nhưng chưa cấu hình LLM để sinh câu trả lời."
    body = "Mình đã truy xuất được các đoạn tài liệu sau đây.\n\n"
    body += "\n\n".join(f"**Nguồn {i+1} — {s['title']}**\n{s['text']}" for i,s in enumerate(sources))
    body += "\n\n**Lưu ý:** Backend/RAG đã hoạt động, nhưng GEMINI_API_KEY chưa được cấu hình nên nội dung hiện là các đoạn trích truy xuất, không phải câu trả lời được LLM sinh."
    return body

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/api/health")
def health():
    return {"ok":True,"service":"StudyBuddy AI","database":"SQLite","rag_enabled":True,"llm_enabled":bool(os.getenv("GEMINI_API_KEY","")),"model":MODEL if os.getenv("GEMINI_API_KEY","") else None,"message":"Backend hoạt động"}

@app.get("/api/stats")
def stats():
    with db() as conn:
        return {"documents":conn.execute("SELECT COUNT(*) FROM documents WHERE user_id=1").fetchone()[0],"chunks":conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0],"questions":conn.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0],"tasks":conn.execute("SELECT COUNT(*) FROM study_tasks WHERE user_id=1").fetchone()[0]}

@app.get("/api/documents")
def list_documents():
    with db() as conn:
        rows = conn.execute("SELECT id,title,subject,body,file_type,created_at FROM documents WHERE user_id=1 ORDER BY created_at DESC").fetchall()
    return {"documents":[dict(r) for r in rows]}

@app.post("/api/documents")
def create_document(item: DocumentIn):
    did = f"doc-{int(datetime.now().timestamp()*1000)}"
    with db() as conn:
        now = utcnow()
        conn.execute("INSERT INTO documents(id,user_id,title,subject,body,file_type,created_at) VALUES(?,1,?,?,?,?,?)", (did,item.title,item.subject,item.body,item.file_type,now))
        rebuild_chunks(conn,did,item.body)
    return {"ok":True,"id":did,"title":item.title,"created_at":now}

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    with db() as conn:
        row = conn.execute("SELECT id FROM documents WHERE id=? AND user_id=1",(document_id,)).fetchone()
        if not row: raise HTTPException(404,"Không tìm thấy tài liệu")
        conn.execute("DELETE FROM documents WHERE id=?",(document_id,))
    return {"ok":True,"deleted":document_id}

@app.post("/api/chat")
def chat(item: ChatIn):
    question = item.question.strip()
    sources = retrieve(question)
    with db() as conn:
        conv = conn.execute("SELECT id FROM conversations WHERE user_id=1 ORDER BY id DESC LIMIT 1").fetchone()
        if conv: conv_id = conv["id"]
        else:
            cur=conn.execute("INSERT INTO conversations(user_id,title,created_at) VALUES(1,?,?)",(question[:80],utcnow())); conv_id=cur.lastrowid
        conn.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(conv_id,"user",question,utcnow()))
    generated = gemini_generate(question,sources)
    mode = "rag_llm" if generated else "rag_retrieval_only"
    answer = generated or local_answer(question,sources)
    with db() as conn:
        cur=conn.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(conv_id,"assistant",answer,utcnow()))
        message_id=cur.lastrowid
        for s in sources: conn.execute("INSERT INTO message_sources(message_id,chunk_id,score) VALUES(?,?,?)",(message_id,s["id"],s["score"]))
    return {"answer":answer,"mode":mode,"sources":[{"id":s["id"],"title":s["title"],"text":s["text"],"score":s["score"]} for s in sources]}

@app.get("/api/schema")
def schema():
    with db() as conn:
        tables=conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return {"tables":[{"name":t["name"],"sql":t["sql"]} for t in tables]}
