import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

class JobDatabase:
    def __init__(self, db_path: str = "job_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create jobs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT UNIQUE,
                        title TEXT NOT NULL,
                        company TEXT,
                        location TEXT,
                        date_posted TEXT,
                        job_description TEXT,
                        salary TEXT,
                        experience_level TEXT,
                        job_type TEXT,
                        source TEXT,
                        url TEXT,
                        skills_required TEXT,
                        skills_matched TEXT,
                        match_score REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create search_logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        search_criteria TEXT,
                        jobs_found INTEGER,
                        jobs_added INTEGER,
                        search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create skills_matches table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS skills_matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT,
                        skill_category TEXT,
                        skill_name TEXT,
                        match_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise
    
    def add_job(self, job_data: Dict) -> bool:
        """Add a new job posting to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if job already exists
                cursor.execute("SELECT id FROM jobs WHERE job_id = ?", (job_data.get('job_id'),))
                if cursor.fetchone():
                    logging.info(f"Job {job_data.get('job_id')} already exists, skipping")
                    return False
                
                # Insert new job
                cursor.execute('''
                    INSERT INTO jobs (
                        job_id, title, company, location, date_posted, 
                        job_description, salary, experience_level, job_type,
                        source, url, skills_required, skills_matched, match_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_data.get('job_id'),
                    job_data.get('title'),
                    job_data.get('company'),
                    job_data.get('location'),
                    job_data.get('date_posted'),
                    job_data.get('job_description'),
                    job_data.get('salary'),
                    job_data.get('experience_level'),
                    job_data.get('job_type'),
                    job_data.get('source'),
                    job_data.get('url'),
                    json.dumps(job_data.get('skills_required', [])),
                    json.dumps(job_data.get('skills_matched', [])),
                    job_data.get('match_score', 0.0)
                ))
                
                conn.commit()
                logging.info(f"Added job: {job_data.get('title')} at {job_data.get('company')}")
                return True
                
        except Exception as e:
            logging.error(f"Error adding job: {e}")
            return False
    
    def get_jobs(self, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict]:
        """Retrieve jobs from database with optional filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM jobs"
                params = []
                
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if key == 'skills_required':
                            conditions.append("skills_required LIKE ?")
                            params.append(f"%{value}%")
                        elif key == 'date_posted':
                            conditions.append("date_posted >= ?")
                            params.append(value)
                        else:
                            conditions.append(f"{key} LIKE ?")
                            params.append(f"%{value}%")
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                columns = [description[0] for description in cursor.description]
                jobs = []
                
                for row in cursor.fetchall():
                    job = dict(zip(columns, row))
                    # Parse JSON fields
                    if job.get('skills_required'):
                        job['skills_required'] = json.loads(job['skills_required'])
                    if job.get('skills_matched'):
                        job['skills_matched'] = json.loads(job['skills_matched'])
                    jobs.append(job)
                
                return jobs
                
        except Exception as e:
            logging.error(f"Error retrieving jobs: {e}")
            return []
    
    def get_jobs_by_match_score(self, min_score: float = 0.5, limit: int = 50) -> List[Dict]:
        """Get jobs sorted by match score"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM jobs 
                    WHERE match_score >= ? 
                    ORDER BY match_score DESC, created_at DESC 
                    LIMIT ?
                ''', (min_score, limit))
                
                columns = [description[0] for description in cursor.description]
                jobs = []
                
                for row in cursor.fetchall():
                    job = dict(zip(columns, row))
                    if job.get('skills_required'):
                        job['skills_required'] = json.loads(job['skills_required'])
                    if job.get('skills_matched'):
                        job['skills_matched'] = json.loads(job['skills_matched'])
                    jobs.append(job)
                
                return jobs
                
        except Exception as e:
            logging.error(f"Error retrieving jobs by match score: {e}")
            return []
    
    def update_job(self, job_id: str, updates: Dict) -> bool:
        """Update an existing job posting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                set_clause += ", updated_at = CURRENT_TIMESTAMP"
                
                query = f"UPDATE jobs SET {set_clause} WHERE job_id = ?"
                params = list(updates.values()) + [job_id]
                
                cursor.execute(query, params)
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logging.error(f"Error updating job: {e}")
            return False
    
    def delete_old_jobs(self, days_old: int = 30) -> int:
        """Delete jobs older than specified days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM jobs 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days_old))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logging.info(f"Deleted {deleted_count} old jobs")
                return deleted_count
                
        except Exception as e:
            logging.error(f"Error deleting old jobs: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total jobs
                cursor.execute("SELECT COUNT(*) FROM jobs")
                stats['total_jobs'] = cursor.fetchone()[0]
                
                # Jobs by source
                cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source")
                stats['jobs_by_source'] = dict(cursor.fetchall())
                
                # Average match score
                cursor.execute("SELECT AVG(match_score) FROM jobs WHERE match_score > 0")
                result = cursor.fetchone()[0]
                stats['avg_match_score'] = round(result, 2) if result else 0
                
                # Recent jobs (last 7 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM jobs 
                    WHERE created_at >= datetime('now', '-7 days')
                ''')
                stats['recent_jobs'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logging.error(f"Error getting statistics: {e}")
            return {}
    
    def export_to_csv(self, filename: str = "jobs_export.csv") -> bool:
        """Export jobs to CSV file"""
        try:
            jobs = self.get_jobs(limit=10000)  # Get all jobs
            if jobs:
                df = pd.DataFrame(jobs)
                df.to_csv(filename, index=False)
                logging.info(f"Exported {len(jobs)} jobs to {filename}")
                return True
            return False
            
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            return False
























