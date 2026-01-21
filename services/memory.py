import datetime
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, asc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "mysql+pymysql://root:root@localhost/dash"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- THE "RELATIONAL" STRUCT ---
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True) # The Phone Number
    role = Column(String(20))                # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- THE APIs ---

@app.get("/history/{user_id}")
def get_history(user_id: str, db: Session = Depends(get_db)):
    # Retrieve all messages for this user, ordered by time
    # This is equivalent to your "Rehydration" step
    rows = db.query(Message).filter(Message.user_id == user_id).order_by(asc(Message.created_at)).all()
    # Map rows to the format the LLM expects
    return [{"role": r.role, "content": r.content} for r in rows]

@app.post("/add_message/{user_id}")
def add_message(user_id: str, role: str, content: str, db: Session = Depends(get_db)):
    # Add just one single message to the conversation
    new_msg = Message(user_id=user_id, role=role, content=content)
    db.add(new_msg)
    db.commit()
    return {"status": "added"}

@app.delete("/history/{user_id}")
def clear_history(user_id: str, db: Session = Depends(get_db)):
    # This is your "Session Reset" logic
    db.query(Message).filter(Message.user_id == user_id).delete()
    db.commit()
    return {"status": "cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)