"""Database manager for tracking generation history"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from .config import Config


class DatabaseManager:
    """Manages SQLite database for generation history"""
    
    def __init__(self) -> None:
        self.config = Config()
        self.db_path: Path = self.config.storage_dir / 'generations.db'
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database and create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    base_model TEXT NOT NULL,
                    finetuned_model TEXT,
                    steps INTEGER,
                    image_size TEXT,
                    num_images INTEGER,
                    seed INTEGER,
                    image_paths TEXT, -- JSON array of local image paths
                    image_urls TEXT,  -- JSON array of original URLs
                    generation_time REAL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    metadata TEXT     -- JSON for additional model-specific data
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON generations(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt ON generations(prompt)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_base_model ON generations(base_model)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_success ON generations(success)
            """)
            
            # Create sessions table for iterative editing
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_timestamp TEXT NOT NULL,
                    updated_timestamp TEXT NOT NULL,
                    initial_image_path TEXT NOT NULL,
                    description TEXT
                )
            """)
            
            # Create session_steps table to track editing steps
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    step_number INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    generation_time REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON session_steps(session_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_step ON session_steps(session_id, step_number)
            """)
    
    def log_generation(
        self,
        prompt: str,
        base_model: str,
        result: Dict[str, Any],
        finetuned_model: Optional[str] = None,
        steps: Optional[int] = None,
        image_size: Optional[str] = None,
        num_images: int = 1,
        generation_time: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log a generation to the database
        
        Args:
            prompt: The text prompt used
            base_model: Base model name (flux-dev, flux-schnell, nano-banana)
            result: Full API response
            finetuned_model: Fine-tuned model name if used
            steps: Number of inference steps
            image_size: Image size parameter
            num_images: Number of images requested
            generation_time: Time taken for generation
            success: Whether generation succeeded
            error_message: Error message if failed
            image_paths: Local paths to saved images
            metadata: Additional model-specific data
            
        Returns:
            ID of the inserted record
        """
        timestamp = datetime.now().isoformat()
        
        # Extract data from API result
        image_urls = []
        seed = None
        actual_generation_time = generation_time
        
        if success and result and 'images' in result:
            image_urls = [img.get('url', '') for img in result['images']]
            seed = result.get('seed')
            if not actual_generation_time and 'timings' in result:
                actual_generation_time = result['timings'].get('inference')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO generations (
                    timestamp, prompt, base_model, finetuned_model, steps,
                    image_size, num_images, seed, image_paths, image_urls,
                    generation_time, success, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, prompt, base_model, finetuned_model, steps,
                image_size, num_images, seed,
                json.dumps(image_paths or []),
                json.dumps(image_urls),
                actual_generation_time, success, error_message,
                json.dumps(metadata or {})
            ))
            
            return cursor.lastrowid
    
    def search_generations(
        self,
        prompt_search: Optional[str] = None,
        base_model: Optional[str] = None,
        finetuned_model: Optional[str] = None,
        success_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search generation history
        
        Args:
            prompt_search: Text to search in prompts (case-insensitive)
            base_model: Filter by base model
            finetuned_model: Filter by fine-tuned model
            success_only: Only return successful generations
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of generation records
        """
        query = "SELECT * FROM generations WHERE 1=1"
        params = []
        
        if prompt_search:
            query += " AND prompt LIKE ?"
            params.append(f"%{prompt_search}%")
        
        if base_model:
            query += " AND base_model = ?"
            params.append(base_model)
        
        if finetuned_model:
            query += " AND finetuned_model = ?"
            params.append(finetuned_model)
        
        if success_only:
            query += " AND success = 1"
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dicts and parse JSON fields
            results = []
            for row in rows:
                result = dict(row)
                result['image_paths'] = json.loads(result['image_paths'])
                result['image_urls'] = json.loads(result['image_urls'])
                result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            
            return results
    
    def get_generation_by_id(self, generation_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific generation by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM generations WHERE id = ?", (generation_id,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result['image_paths'] = json.loads(result['image_paths'])
                result['image_urls'] = json.loads(result['image_urls'])
                result['metadata'] = json.loads(result['metadata'])
                return result
            
            return None
    
    def get_recent_generations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent generations"""
        return self.search_generations(limit=limit, success_only=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Total generations
            total = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
            
            # Successful generations
            successful = conn.execute("SELECT COUNT(*) FROM generations WHERE success = 1").fetchone()[0]
            
            # By base model
            model_stats = conn.execute("""
                SELECT base_model, COUNT(*) as count 
                FROM generations WHERE success = 1 
                GROUP BY base_model
            """).fetchall()
            
            # Average generation time by model
            time_stats = conn.execute("""
                SELECT base_model, AVG(generation_time) as avg_time 
                FROM generations 
                WHERE success = 1 AND generation_time IS NOT NULL
                GROUP BY base_model
            """).fetchall()
            
            return {
                'total_generations': total,
                'successful_generations': successful,
                'failed_generations': total - successful,
                'success_rate': (successful / total * 100) if total > 0 else 0,
                'model_counts': {row[0]: row[1] for row in model_stats},
                'avg_generation_times': {row[0]: round(row[1], 2) for row in time_stats}
            }
    
    def delete_generation(self, generation_id: int) -> bool:
        """Delete a generation record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM generations WHERE id = ?", (generation_id,))
            return cursor.rowcount > 0
    
    def update_image_paths(self, generation_id: int, image_paths: List[str]) -> bool:
        """Update image paths for a generation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE generations SET image_paths = ? WHERE id = ?",
                (json.dumps(image_paths), generation_id)
            )
            return cursor.rowcount > 0
    
    def get_latest_generation_id(self) -> Optional[int]:
        """Get the ID of the most recent generation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM generations ORDER BY timestamp DESC LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None
    
    def cleanup_old_generations(self, keep_days: int = 30) -> int:
        """Remove generations older than specified days"""
        cutoff_date = datetime.now().replace(day=datetime.now().day - keep_days).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM generations WHERE timestamp < ?", 
                (cutoff_date,)
            )
            return cursor.rowcount
    
    # Session management methods
    def create_session(self, name: str, initial_image_path: str, description: str = "") -> int:
        """Create a new editing session"""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sessions (name, created_timestamp, updated_timestamp, initial_image_path, description)
                VALUES (?, ?, ?, ?, ?)
            """, (name, timestamp, timestamp, initial_image_path, description))
            return cursor.lastrowid
    
    def add_session_step(self, session_id: int, step_number: int, prompt: str, 
                        image_path: str, success: bool, error_message: str = None,
                        generation_time: float = None) -> int:
        """Add a step to an editing session"""
        timestamp = datetime.now().isoformat()
        
        # Update session timestamp
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions SET updated_timestamp = ? WHERE id = ?
            """, (timestamp, session_id))
            
            cursor = conn.execute("""
                INSERT INTO session_steps 
                (session_id, step_number, prompt, image_path, timestamp, success, error_message, generation_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, step_number, prompt, image_path, timestamp, success, error_message, generation_time))
            return cursor.lastrowid
    
    def get_sessions(self) -> List[Dict[str, Any]]:
        """Get all editing sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT s.*, COUNT(ss.id) as step_count,
                       MAX(ss.timestamp) as last_step_timestamp
                FROM sessions s
                LEFT JOIN session_steps ss ON s.id = ss.session_id
                GROUP BY s.id
                ORDER BY s.updated_timestamp DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a session by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT s.*, COUNT(ss.id) as step_count
                FROM sessions s
                LEFT JOIN session_steps ss ON s.id = ss.session_id
                WHERE s.id = ?
                GROUP BY s.id
            """, (session_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_session_steps(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all steps for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM session_steps 
                WHERE session_id = ? 
                ORDER BY step_number ASC
            """, (session_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_session(self, session_id: int) -> bool:
        """Delete a session and all its steps"""
        with sqlite3.connect(self.db_path) as conn:
            # Delete steps first (foreign key constraint)
            conn.execute("DELETE FROM session_steps WHERE session_id = ?", (session_id,))
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0