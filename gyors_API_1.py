from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect

#http://127.0.0.1:8000/docs#/
#uvicorn gyors_API_1:app --host 0.0.0.0 --port 8000 --reload
#python -m uvicorn gyors_API_1:app --host 0.0.0.0 --port 8000 --reload
"""Szabályként jegyezd meg az alapokhoz: ha új adatot akarsz létrehozni és 
menteni az adatbázisba, mindig kelleni fog a db.add(...), a db.commit() 
(ami véglegesíti a mentést), és a db.refresh(...) parancs. Ha csak olvasni 
akarsz, akkor a db.query(...) parancsot kell használnod a megfelelő szűrésekkel 
(mint a .filter() vagy a .all())."""




app = FastAPI()

DATE_BASE_URL = "sqlite:///./test.db"
engine = create_engine(DATE_BASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base =declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    friends = Column(JSON, default=list)

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    friends: List[str] = []

    @field_validator("friends", mode="before")
    def is_list(cls, v):
        if v is None:
            return []
        return v
    model_config = {
        "from_attributes": True
    }

class UserCreate(BaseModel):
    name: str
    email: str

class ChatCreate(BaseModel):
    name: str

class ChatResponse(BaseModel):
    id: int
    name: str

class ChatMemberCreate(BaseModel):
    user_id: int
    chat_id: int

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

class ChatMember(Base):
    __tablename__ = "chat_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chat_id = Column(Integer, ForeignKey("chats.id"))

class Massange(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    text = Column(String)
    chat_id = Column(Integer)
    created_at = Column(String)

class MessageCreate(BaseModel):
    name: str
    chat_id: int
    text: str

class MessageResponse(BaseModel):
    id: int
    name: str
    text: str
    chat_id: int
    created_at: str

    model_config = {
        "from_attributes": True
    }

from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
        self.user_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, chat_id: int, websocket: WebSocket):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].remove(websocket)

    async def broadcast(self, chat_id: int, message: str):
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                await connection.send_text(message)

    async def connect_user(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

    def disconnect_user(self, user_id: int, websocket: WebSocket):
        if user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)

    async def notify_user(self, user_id: int, message: str):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                await connection.send_text(message)

manager = ConnectionManager()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



Base.metadata.create_all(bind=engine)

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db:Session=Depends(get_db)):
    letezo_user = db.query(User).filter(User.email == user.email).first()
    if letezo_user:
        raise HTTPException(status_code=400, detail="Ez az email már létezik")
    db_user = User(name=user.name, email=user.email, friends=["Note"])
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
      

@app.get("/users/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit:int= 10, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=(UserResponse))
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user




@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.name = user.name if user.name is not None else db_user.name
    db_user.email = user.email if user.email is not None else db_user.email
    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/users/{user_id}", response_model=UserResponse)
def delte_user(user_id:int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return db_user



@app.post("/messages/", response_model=MessageResponse)
async def send(message: MessageCreate, db: Session = Depends(get_db)):
    chat_exis = db.query(Chat).filter(Chat.id == message.chat_id).first()
    if not chat_exis:
        raise HTTPException(status_code=404, detail="there is no chat whit this id")
    existing_user = db.query(User).filter(User.name == message.name).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"There is no user named: {message.name}")
    db_messenge = Massange(name=message.name, text=message.text, chat_id=message.chat_id, created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    
    db.add(db_messenge)
    db.commit()
    db.refresh(db_messenge)
    await manager.broadcast(message.chat_id, "new_messenge")
    return db_messenge


@app.get("/messages/", response_model=List[MessageResponse])
def read_messages(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    db_m = db.query(Massange).order_by(Massange.id.desc()).offset(skip).limit(limit).all()
    return db_m


@app.delete("/messages/", response_model=MessageResponse)
def delte_messege(messege_id: int, db: Session = Depends(get_db)):
    db_messege = db.query(Massange).filter(messege_id == Massange.id).first()
    if db_messege is None:
        raise HTTPException(status_code=404, detail="Messege not found")
    db.delete(db_messege)
    db.commit()
    return db_messege

@app.put("/users/", response_model=UserResponse)
def friend_add(self_name: str, friend_name: str, db: Session = Depends(get_db)):
    exising_user = db.query(User).filter(User.name == friend_name).first()
    self_user = db.query(User).filter(User.name == self_name).first()
    
    if not self_user or not exising_user:
        raise HTTPException(status_code=404, detail="There is no name like this.")
    if self_name == friend_name:
        raise HTTPException(status_code=400, detail="You cannot add yourself as a friend.")
    
    current_friends = self_user.friends if self_user.friends is not None else []
    
    if friend_name in current_friends:
        raise HTTPException(status_code=400, detail=f"{friend_name} is already your friend")
    
    updated_friends = list(current_friends)
    updated_friends.append(friend_name)
    self_user.friends = updated_friends
    flag_modified(self_user, "friends")
    
    db.commit()
    db.refresh(self_user)
    
    return self_user


@app.get("/users/by-name/{name}", response_model=UserResponse)
def read_user_by_name(name: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == name).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/chat/", response_model=ChatResponse)
async def create_chat(chat: ChatCreate, user_id: int, db: Session=Depends(get_db)):
    new_chat = Chat(name=chat.name)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    new_member = ChatMember(chat_id=new_chat.id, user_id=user_id)
    db.add(new_member)
    db.commit()
    await manager.notify_user(user_id, "REFRESH_CHATS")
    return new_chat

@app.post("/chats/{chat_id}/members/")
async def members_add_to_chat(chat_id: int, user_id: int, db: Session=Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    already_member = db.query(ChatMember).filter(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id).first()

    if already_member:
        raise HTTPException(status_code=400, detail="This user is already a member")

    new_member = ChatMember(chat_id=chat_id, user_id=user_id)
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    await manager.notify_user(user_id, "REFRESH_CHATS")
    return {"message": "User added successfully"}

@app.get("/users/{user_id}/chats/", response_model=List[ChatResponse])
def users_chats(user_id: int, db: Session=Depends(get_db)):
    memberships = db.query(ChatMember).filter(ChatMember.user_id == user_id).all()
    if not memberships:
        return []
    chat_ids = [m.chat_id for m in memberships]
    chats = db.query(Chat).filter(Chat.id.in_(chat_ids)).all()
    return chats

@app.get("/chats/{chat_id}/messages/", response_model=List[MessageResponse])
def get_chat_messeges(user_id: int, chat_id: int, db: Session=Depends(get_db)):
    ellenorzes = db.query(ChatMember).filter(ChatMember.user_id == user_id, ChatMember.chat_id == chat_id).first()

    if ellenorzes:
        messenges = db.query(Massange).filter(Massange.chat_id == chat_id).all()

        return messenges
    raise HTTPException(status_code=403, detail="you do not have pass to this chat")

@app.get("/chats/", response_model=List[ChatResponse])
def read_chats(skip: int = 0, limit:int= 10, db: Session = Depends(get_db)):
    chats = db.query(Chat).offset(skip).limit(limit).all()
    return chats


@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    await manager.connect(chat_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)

@app.websocket("/ws/user/{user_id}")
async def user_websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect_user(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_user(user_id, websocket)
