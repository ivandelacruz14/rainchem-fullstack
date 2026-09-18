from datetime import datetime
from app.extensions import db


class KnowledgeEntry(db.Model):
    __tablename__ = "knowledge_base"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    hits = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "status": self.status,
            "hits": self.hits,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class ChatLog(db.Model):
    __tablename__ = "chat_logs"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    matched_knowledge_id = db.Column(db.Integer, db.ForeignKey("knowledge_base.id"), nullable=True)
    confidence = db.Column(db.Integer, nullable=False, default=0)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "resolved": self.resolved,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    channel = db.Column(db.String(20), nullable=False, default="email")
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
