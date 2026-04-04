"""In-memory debate session store"""
import uuid
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Message:
    id: str
    agent_key: str
    agent_name: str
    role: str  # "user" or "assistant" or "system"
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")

@dataclass
class Agent:
    key: str
    name: str
    emoji: str
    color: str
    role: str  # main_planner, researcher, skeptic, optimist, realist, critic, synthesizer
    prompt_template: str
    vote: Optional[str] = None
    vote_reason: Optional[str] = None

@dataclass 
class DebateGroup:
    id: str
    name: str
    description: str
    agents: List[Agent]
    messages: List[Message] = field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 3
    round_votes: Dict[int, Dict[str, str]] = field(default_factory=dict)  # round -> {agent_key: vote}
    group_vote: Optional[str] = None

@dataclass
class DebateSession:
    id: str
    topic: str
    user_input: str
    created_at: str
    status: str  # "active", "completed", "failed"
    groups: List[DebateGroup] = field(default_factory=list)
    main_planner_summary: Optional[str] = None
    final_answer: Optional[str] = None
    total_rounds: int = 3
    current_phase: str = "planning"  # planning, debating, voting, summarizing, done
    vote_options: List[str] = field(default_factory=list)  # e.g. ["100万以下", "100-300万", "500万以上"]
    events: List[Dict] = field(default_factory=list)  # SSE events for streaming
    
    def cleanup(self):
        """Clean up session data"""
        self.groups.clear()
        self.events.clear()
        self.status = "cleanup"

class SessionStore:
    """In-memory session storage"""
    def __init__(self):
        self.sessions: Dict[str, DebateSession] = {}
        self.lock = threading.Lock()
        self.expiry_seconds = 3600  # Sessions expire after 1 hour
        self._start_cleanup()  # Start background cleanup thread
    
    def create_session(self, topic: str, user_input: str) -> str:
        session_id = str(uuid.uuid4())[:8]
        session = DebateSession(
            id=session_id,
            topic=topic,
            user_input=user_input,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status="active"
        )
        with self.lock:
            self.sessions[session_id] = session
        # Clean up old sessions
        return session_id
    
    def get_session(self, session_id: str) -> Optional[DebateSession]:
        with self.lock:
            return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].cleanup()
                del self.sessions[session_id]
    
    def _cleanup_expired(self):
        """Remove expired sessions (background thread)"""
        while True:
            try:
                import time as _time
                _time.sleep(300)  # Check every 5 minutes
                now = time.time()
                expired = []
                with self.lock:
                    for sid, sess in self.sessions.items():
                        try:
                            created = datetime.strptime(sess.created_at, "%Y-%m-%d %H:%M:%S")
                            age = (datetime.now() - created).total_seconds()
                            if age > self.expiry_seconds:
                                expired.append(sid)
                        except:
                            pass
                    for sid in expired:
                        sess = self.sessions.pop(sid, None)
                        if sess:
                            sess.cleanup()
                    if expired:
                        print(f"[Store] Cleaned {len(expired)} expired sessions")
            except Exception as e:
                print(f"[Store] Cleanup error: {e}")

    def _start_cleanup(self):
        t = threading.Thread(target=self._cleanup_expired, daemon=True)
        t.start()
        print("[Store] Cleanup thread started (TTL=%ds)" % self.expiry_seconds)

# Global store instance
store = SessionStore()