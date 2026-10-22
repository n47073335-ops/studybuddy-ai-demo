PRAGMA foreign_keys = ON;
CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE documents (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, file_type TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE document_chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, chunk_index INTEGER NOT NULL, chunk_text TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(document_id,chunk_index));
CREATE TABLE conversations (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE messages (id INTEGER PRIMARY KEY, conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE message_sources (id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE, chunk_id TEXT NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE, score REAL NOT NULL);
CREATE TABLE study_tasks (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL, subject TEXT NOT NULL, due_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('todo','done')));
