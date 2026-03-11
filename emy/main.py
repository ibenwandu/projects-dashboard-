"""
Emy main agent loop - primary orchestration engine.

Coordinates all sub-agents, skills, and scheduling.
Runs as a persistent process with configurable tick interval.
"""

import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import time
from typing import Optional

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from emy.core.database import EMyDatabase
from emy.core.disable_guard import EMyDisableGuard
from emy.core.delegation_engine import EMyDelegationEngine
from emy.core.approval_gate import EMyApprovalGate
from emy.core.task_router import EMyTaskRouter
from emy.core.skill_improver import EMySkillImprover
from emy.scheduler.emy_scheduler import EMyScheduler
from emy.agents.trading_agent import TradingAgent
from emy.agents.job_search_agent import JobSearchAgent
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.project_monitor_agent import ProjectMonitorAgent
from emy.agents.research_agent import ResearchAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('emy/data/emy.log')
    ]
)
logger = logging.getLogger('EMyAgentLoop')


class EMyAgentLoop:
    """Main Emy orchestration loop."""

    def __init__(self):
        """Initialize Emy agent loop."""
        load_dotenv()

        self.db = EMyDatabase()
        self.db.initialize_schema()
        self.disable_guard = EMyDisableGuard()
        self.scheduler = EMyScheduler()
        self.delegation_engine = EMyDelegationEngine(database=self.db)
        self.approval_gate = EMyApprovalGate(self.db)
        self.task_router = EMyTaskRouter(self.delegation_engine, self.approval_gate)

        # Initialize skill improver (requires skill_loader and skill_registry)
        from emy.skills.skill_loader import EMySkillLoader
        from emy.skills.skill_registry import EMySkillRegistry
        from emy.tools.notification_tool import NotificationTool

        self.skill_loader = EMySkillLoader()
        self.skill_registry = EMySkillRegistry()
        self.skill_improver = EMySkillImprover(
            self.db,
            self.skill_loader,
            self.skill_registry,
            NotificationTool()
        )

        self.running = True
        self.last_tick = None
        self.tick_interval_seconds = 60  # Main loop runs every 60 seconds

        # Register agents
        self.delegation_engine.register_agent('TradingAgent', TradingAgent)
        self.delegation_engine.register_agent('JobSearchAgent', JobSearchAgent)
        self.delegation_engine.register_agent('KnowledgeAgent', KnowledgeAgent)
        self.delegation_engine.register_agent('ProjectMonitorAgent', ProjectMonitorAgent)
        self.delegation_engine.register_agent('ResearchAgent', ResearchAgent)

        # Register Phase 1 + Phase 2 + Phase 3 + Phase 4 jobs
        self._register_phase1_jobs()
        self._register_phase2_jobs()
        self._register_phase3_jobs()
        self._register_phase4_jobs()

        logger.info("[INIT] EMyAgentLoop initialized with all agents and skill improver")

    def boot(self):
        """Boot Emy and verify system readiness."""
        logger.info("[BOOT] Emy booting...")

        # Check disable switch
        if self.disable_guard.is_disabled():
            logger.error("[DISABLED] Emy is disabled (.emy_disabled file present). Exiting.")
            sys.exit(1)

        # Verify database
        try:
            task_id = self.db.log_task('internal', 'system', 'boot', 'Emy bootstrap')
            self.db.update_task(task_id, 'completed', json.dumps({'status': 'ready'}))
            logger.info("[OK] Database verified")
        except Exception as e:
            logger.error(f"[ERR] Database verification failed: {e}")
            sys.exit(1)

        # Check API budget
        daily_spend = self.db.get_daily_spend()
        daily_budget = float(os.getenv('EMY_DAILY_BUDGET_USD', '5.00'))
        spend_percent = (daily_spend / daily_budget * 100) if daily_budget > 0 else 0
        logger.info(f"[BUDGET] Daily budget: ${daily_spend:.2f} / ${daily_budget:.2f} ({spend_percent:.1f}%)")

        if spend_percent >= 100:
            logger.warning("[WARN] Daily budget EXCEEDED. Disabling scheduled tasks.")
            self.disable_guard.set_disabled(True)
            return False

        logger.info("[OK] Emy boot complete")
        return True

    def _register_phase1_jobs(self):
        """Register Phase 1 trading monitoring jobs."""
        # Trading health check every 15 minutes (900 seconds)
        self.scheduler.register_job(
            'trading_health_check',
            self._job_trading_health_check,
            900  # 15 minutes
        )

        logger.info("[JOBS] Phase 1 trading jobs registered")

    def _job_trading_health_check(self):
        """Job handler for trading health check."""
        try:
            task_id = self.db.log_task('scheduler', 'trading', 'health_check',
                                      'Trading health monitoring')
            success, results = self.delegation_engine.spawn(TradingAgent, task_id)

            if success:
                self.db.update_task(task_id, 'completed',
                                   json.dumps(results))
                logger.info("[JOB] trading_health_check completed")
            else:
                self.db.update_task(task_id, 'failed',
                                   error_message=results.get('error', 'unknown'))
                logger.warning("[JOB] trading_health_check failed")
        except Exception as e:
            logger.error(f"[JOB] trading_health_check error: {e}")

    def _register_phase2_jobs(self):
        """Register Phase 2 job search jobs."""
        # Job search daily at 09:00 EST (32400 seconds from midnight)
        self.scheduler.register_job(
            'job_search_daily',
            self._job_search_daily,
            86400  # Run daily (86400 seconds)
        )

        # Resume tailoring daily at 10:00 EST (36000 seconds from midnight)
        self.scheduler.register_job(
            'resume_tailor_approved',
            self._job_tailor_resume,
            86400  # Run daily
        )

        logger.info("[JOBS] Phase 2 job search jobs registered")

    def _job_search_daily(self):
        """Job handler for daily job search."""
        try:
            task_id = self.db.log_task('scheduler', 'job_search', 'search_daily',
                                      'Daily job search across 4 platforms')
            success, results = self.delegation_engine.spawn(JobSearchAgent, task_id)

            if success:
                self.db.update_task(task_id, 'completed',
                                   json.dumps(results))
                logger.info(f"[JOB] job_search_daily: {results.get('jobs_found')} jobs found")
            else:
                self.db.update_task(task_id, 'failed',
                                   error_message=results.get('error', 'unknown'))
                logger.warning("[JOB] job_search_daily failed")
        except Exception as e:
            logger.error(f"[JOB] job_search_daily error: {e}")

    def _job_tailor_resume(self):
        """Job handler for resume tailoring."""
        try:
            task_id = self.db.log_task('scheduler', 'job_search', 'tailor_resume',
                                      'Tailor resumes for high-scoring jobs')
            success, results = self.delegation_engine.spawn(JobSearchAgent, task_id)

            if success:
                self.db.update_task(task_id, 'completed',
                                   json.dumps(results))
                logger.info(f"[JOB] resume_tailor_approved: {results.get('jobs_tailored')} tailored")
            else:
                self.db.update_task(task_id, 'failed',
                                   error_message=results.get('error', 'unknown'))
                logger.warning("[JOB] resume_tailor_approved failed")
        except Exception as e:
            logger.error(f"[JOB] resume_tailor_approved error: {e}")

    def _register_phase3_jobs(self):
        """Register Phase 3 knowledge management jobs."""
        # Obsidian dashboard update every 60 minutes (3600 seconds)
        self.scheduler.register_job(
            'obsidian_dashboard_update',
            self._job_update_obsidian,
            3600  # Run every 60 minutes
        )

        # Memory persistence every 4 hours (14400 seconds)
        self.scheduler.register_job(
            'memory_persist',
            self._job_persist_memory,
            14400  # Every 4 hours
        )

        logger.info("[JOBS] Phase 3 knowledge management jobs registered")

    def _register_phase4_jobs(self):
        """Register Phase 4 approval and self-improvement jobs."""
        # Skill improvement sweep daily at 23:00 EST (82800 seconds from midnight)
        self.scheduler.register_job(
            'skill_improvement_sweep',
            self._job_skill_improvement,
            86400  # Run daily
        )

        logger.info("[JOBS] Phase 4 self-improvement jobs registered")

    def _job_update_obsidian(self):
        """Job handler for Obsidian dashboard update."""
        try:
            task_id = self.db.log_task('scheduler', 'knowledge', 'update_obsidian',
                                      'Update Obsidian dashboard with project metrics')
            success, results = self.delegation_engine.spawn(KnowledgeAgent, task_id)

            if success:
                self.db.update_task(task_id, 'completed',
                                   json.dumps(results))
                logger.info("[JOB] obsidian_dashboard_update completed")
            else:
                self.db.update_task(task_id, 'failed',
                                   error_message=results.get('error', 'unknown'))
                logger.warning("[JOB] obsidian_dashboard_update failed")
        except Exception as e:
            logger.error(f"[JOB] obsidian_dashboard_update error: {e}")

    def _job_persist_memory(self):
        """Job handler for memory persistence."""
        try:
            task_id = self.db.log_task('scheduler', 'knowledge', 'persist_memory',
                                      'Persist findings and decisions to MEMORY.md')
            success, results = self.delegation_engine.spawn(KnowledgeAgent, task_id)

            if success:
                self.db.update_task(task_id, 'completed',
                                   json.dumps(results))
                logger.info("[JOB] memory_persist completed")
            else:
                self.db.update_task(task_id, 'failed',
                                   error_message=results.get('error', 'unknown'))
                logger.warning("[JOB] memory_persist failed")
        except Exception as e:
            logger.error(f"[JOB] memory_persist error: {e}")

    def _job_skill_improvement(self):
        """Job handler for skill improvement sweep."""
        try:
            task_id = self.db.log_task('scheduler', 'system', 'skill_improvement',
                                      'Sweep for underperforming skills and improve')

            # Find underperforming skills
            underperformers = self.skill_improver.find_underperforming_skills()

            if not underperformers:
                self.db.update_task(task_id, 'completed',
                                   json.dumps({'skills_improved': 0, 'status': 'all_healthy'}))
                logger.info("[JOB] skill_improvement_sweep: no underperformers")
                return

            # Improve each skill
            improvements = []
            for skill_info in underperformers:
                success, result = self.skill_improver.improve_skill(skill_info['name'])
                if success:
                    improvements.append(result)
                    logger.info(f"[JOB] Improved skill: {skill_info['name']}")

            self.db.update_task(task_id, 'completed',
                               json.dumps({'skills_improved': len(improvements),
                                         'improvements': improvements}))
            logger.info(f"[JOB] skill_improvement_sweep completed: {len(improvements)} skills improved")

        except Exception as e:
            logger.error(f"[JOB] skill_improvement_sweep error: {e}")

    def tick(self):
        """Main loop tick - runs every 60 seconds."""
        self.last_tick = datetime.now()

        # Check disable switch
        if self.disable_guard.is_disabled():
            logger.warning("Emy is disabled. Skipping tasks.")
            return

        # Check budget
        daily_spend = self.db.get_daily_spend()
        daily_budget = float(os.getenv('EMY_DAILY_BUDGET_USD', '5.00'))

        if daily_spend >= daily_budget * 0.8:
            logger.warning(f"[WARN] Budget warning: {daily_spend:.2f} / {daily_budget:.2f}")
            # Still allow tasks to run; will stop at 100%

        if daily_spend >= daily_budget:
            logger.error(f"[ERR] Daily budget exceeded. Disabling Emy.")
            self.disable_guard.set_disabled(True)
            return

        # Clean up expired approval requests
        self.approval_gate.auto_reject_expired()

        # Execute scheduled jobs
        executed_jobs = self.scheduler.tick(self.last_tick)
        if executed_jobs:
            logger.info(f"[SCHEDULER] Executed: {', '.join(executed_jobs)}")

    def shutdown(self):
        """Clean shutdown."""
        self.running = False
        logger.info("🛑 Emy shutdown")

    def run(self):
        """Main loop - runs until interrupted."""
        if not self.boot():
            return

        logger.info("[RUN] Emy main loop started. Press Ctrl+C to stop.")

        try:
            while self.running:
                self.tick()
                time.sleep(self.tick_interval_seconds)
        except KeyboardInterrupt:
            logger.info("\n[INTERRUPT] Interrupt received")
        finally:
            self.shutdown()


import json  # Import at end to avoid circular imports


def main():
    """Entry point."""
    loop = EMyAgentLoop()
    loop.run()


if __name__ == '__main__':
    main()
