"""Main application: LLM analysis workflow and entry point monitoring"""

import os
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
import pytz
from src.drive_reader import DriveReader
from src.data_formatter import DataFormatter
from src.llm_analyzer import LLMAnalyzer
from src.gemini_synthesizer import GeminiSynthesizer
from src.email_sender import EmailSender
from src.recommendation_parser import RecommendationParser
from src.price_monitor import PriceMonitor
from src.alert_manager import AlertManager
from src.alert_history import AlertHistory
from src.scheduler import AnalysisScheduler, AgentScheduler
from src.logger import setup_logger

# Multi-agent system components (Phase 1-6 complete)
try:
    from agents.orchestrator_agent import OrchestratorAgent
    AGENT_SYSTEM_AVAILABLE = True
except ImportError:
    AGENT_SYSTEM_AVAILABLE = False
    logger = setup_logger()
    logger.warning("Multi-agent system not available (agents not installed)")

# NEW: RL Components
from src.trade_alerts_rl import (
    RecommendationDatabase,
    RecommendationParser as RLRecommendationParser,
    LLMLearningEngine
)
from src.daily_learning import run_daily_learning, should_run_learning
from src.market_bridge import MarketBridge

# Market state API server (optional - serves market_state.json via HTTP)
try:
    from src.market_state_server import MarketStateServer
    MARKET_STATE_SERVER_AVAILABLE = True
except ImportError:
    MARKET_STATE_SERVER_AVAILABLE = False

load_dotenv()
logger = setup_logger()

class TradeAlertSystem:
    """Main trading alert system"""

    # Timing constants (seconds unless noted)
    STATUS_LOG_INTERVAL = 10       # Log status every N main-loop checks
    WEIGHT_RELOAD_INTERVAL = 3600  # Reload LLM weights every hour
    LEARNING_CHECK_INTERVAL = 3600 # Throttle: only trigger learning once per hour
    ANALYSIS_MIN_INTERVAL = 300    # Minimum gap between consecutive analyses (5 min)

    def __init__(self):
        """Initialize system"""
        # Configuration
        try:
            self.check_interval = int(os.getenv('CHECK_INTERVAL', 60))
        except ValueError:
            logger.warning("CHECK_INTERVAL must be an integer — defaulting to 60 seconds")
            self.check_interval = 60
        
        # Initialize components via factory (override _build_components() for testing)
        self._build_components()
        
        # Market state API server (serves market_state.json via HTTP for Scalp-Engine)
        self.market_state_server = None
        if MARKET_STATE_SERVER_AVAILABLE:
            try:
                server_port = int(os.getenv('MARKET_STATE_SERVER_PORT', 5001))
                self.market_state_server = MarketStateServer(port=server_port)
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize market state server: {e}")
        
        # NEW: RL components
        # Enable entry price validation to filter unrealistic entries
        # Use persistent disk on Render, default location for local development
        db_path = os.getenv('RL_DATABASE_PATH')
        if not db_path:
            # Use persistent disk if available, otherwise default location
            if os.path.exists('/var/data'):
                db_path = '/var/data/trade_alerts_rl.db'
                logger.info(f"📦 Using persistent disk for RL database: {db_path}")
            else:
                # Local development - use data directory
                data_dir = Path(__file__).parent / 'data'
                data_dir.mkdir(exist_ok=True)
                db_path = str(data_dir / 'trade_alerts_rl.db')
                logger.info(f"📦 Using local database for RL: {db_path}")
        self.rl_db = RecommendationDatabase(db_path=db_path, validate_entries=True)
        self.rl_parser = RLRecommendationParser()
        self.learning_engine = LLMLearningEngine(self.rl_db)

        # ENTRY POINT HIT log throttle: (pair, direction) -> last INFO log time (consol-recommend2 Phase 1.5)
        self._entry_point_hit_last_logged = {}
        self._entry_point_hit_window_seconds = 600  # 10 min

        # Load learned weights
        self.llm_weights = self._load_llm_weights()
        
        # State
        self.opportunities = []
        self.last_analysis_time = None
        self.last_agent_run_time = None  # Track agent workflow execution
        self.last_learning_check = None
        self.last_weight_reload = None  # Track last weight reload time
        self.latest_recommendation_file = None
        
        logger.info("✅ Trade Alert System initialized")
        logger.info(f"🧠 RL System: Active")
        logger.info(f"⚖️  Current LLM Weights: {self._format_weights()}")
    
    def _build_components(self):
        """Instantiate all service components. Override in tests to inject mocks."""
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
        if not folder_id:
            logger.error("GOOGLE_DRIVE_FOLDER_ID not set in environment variables")
            logger.error("Please set GOOGLE_DRIVE_FOLDER_ID in Render Dashboard → Environment")
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID environment variable is required")

        self.drive_reader = DriveReader(folder_id)
        self.data_formatter = DataFormatter()
        self.llm_analyzer = LLMAnalyzer()
        self.gemini_synthesizer = GeminiSynthesizer()
        self.email_sender = EmailSender()
        self.parser = RecommendationParser()
        self.price_monitor = PriceMonitor()
        self.alert_manager = AlertManager()
        self.alert_history = AlertHistory()
        self.scheduler = AnalysisScheduler()
        self.agent_scheduler = AgentScheduler() if AGENT_SYSTEM_AVAILABLE else None

    def _should_run_analysis(self, current_time) -> bool:
        """Return True if a scheduled analysis should run now."""
        if not self.scheduler.should_run_analysis(current_time):
            return False
        if self.last_analysis_time is None:
            return True
        elapsed = (current_time - self.last_analysis_time).total_seconds()
        return elapsed > self.ANALYSIS_MIN_INTERVAL

    def _should_run_agents(self, current_time) -> bool:
        """Return True if agents should run at current time."""
        if not AGENT_SYSTEM_AVAILABLE or not self.agent_scheduler:
            return False
        if not self.agent_scheduler.should_run_agents(current_time):
            return False
        if self.last_agent_run_time is None:
            return True
        # Minimum interval to prevent duplicate runs (5 minutes)
        elapsed = (current_time - self.last_agent_run_time).total_seconds()
        return elapsed > self.ANALYSIS_MIN_INTERVAL

    def _run_agents(self, current_time: datetime):
        """Run the multi-agent workflow (Phase 1-6 complete)."""
        if not AGENT_SYSTEM_AVAILABLE:
            logger.warning("⚠️ Multi-agent system not available")
            return False

        # NOTE: 4-phase agent system (Phases 2-5) was removed in favor of modular Log Backup Agent.
        # The broken agents (Analyst, Forex Expert, Coding Expert, Orchestrator) are no longer available.
        # If you need multi-agent workflows, they must be rebuilt using the modular foundation.
        logger.info("ℹ️ Multi-agent workflow system has been refactored. See agents/README.md for details.")
        return False

    def _sync_agent_results_locally(self):
        """Sync agent results from Render to local machine."""
        try:
            from agents.sync_render_results import RenderSync

            logger.info("🔄 Syncing agent results to local machine...")
            sync = RenderSync()

            # If database exists locally, extract and update coordination log
            if sync.local_db.exists():
                cycle_data = sync.extract_latest_cycle()
                if cycle_data:
                    sync.update_coordination_log(cycle_data)
                    logger.info(f"✅ Synced Cycle #{cycle_data['cycle_number']} results to coordination.md")
            else:
                logger.info("ℹ️ Local database not found - coordination.md not updated (will be synced on next manual run)")
        except ImportError:
            logger.debug("Sync module not available (normal for local-only runs)")
        except Exception as e:
            logger.warning(f"⚠️ Error syncing results: {e}")

    def _load_llm_weights(self) -> dict:
        """Load latest learned weights from database"""
        try:
            weights = self.learning_engine.calculate_llm_weights()
            if weights and sum(weights.values()) > 0:
                # Log weight calculation details (use INFO so it shows in logs)
                logger.info(f"📊 Loaded LLM weights from database: {weights}")
                return weights
            else:
                logger.warning("⚠️ LLM weights calculation returned empty or zero weights - using defaults")
        except Exception as e:
            logger.error(f"Error loading LLM weights from database: {e} - using defaults", exc_info=True)
        
        # Default equal weights if no learning yet
        default_weights = {
            'chatgpt': 0.25,
            'gemini': 0.25,
            'claude': 0.25,
            'synthesis': 0.25
        }
        logger.info(f"📊 Using default LLM weights: {default_weights}")
        return default_weights
    
    def _format_weights(self) -> str:
        """Format weights for display"""
        return ", ".join([f"{k}: {v*100:.0f}%" for k, v in self.llm_weights.items()])

    def run(self):
        """Run main loop"""
        logger.info("🚀 Starting Trade Alert System...")
        
        # Note: Market state API server is started separately when running as web service
        # (see run_web_service.py). When running as worker, server is not started here.
        # This allows the same code to work in both web and worker modes.
        
        logger.info("Press Ctrl+C to stop")
        
        # Show next analysis time
        next_analysis = self.scheduler.get_next_analysis_time()
        est_tz = pytz.timezone('America/New_York')
        if next_analysis:
            # Convert to EST for display
            if next_analysis.tzinfo is None:
                next_analysis_utc = pytz.UTC.localize(next_analysis)
            else:
                next_analysis_utc = next_analysis
            next_analysis_est = next_analysis_utc.astimezone(est_tz)
            logger.info(f"⏰ Next scheduled analysis: {next_analysis_est.strftime('%Y-%m-%d %H:%M %Z')} (EST/EDT)")
        else:
            logger.info("⏰ No scheduled analysis times configured")

        # Show next agent workflow time
        if AGENT_SYSTEM_AVAILABLE and self.agent_scheduler:
            next_agent_run = self.agent_scheduler.get_next_agent_run_time()
            if next_agent_run:
                if next_agent_run.tzinfo is None:
                    next_agent_utc = pytz.UTC.localize(next_agent_run)
                else:
                    next_agent_utc = next_agent_run
                next_agent_est = next_agent_utc.astimezone(est_tz)
                logger.info(f"🤖 Next agent workflow: {next_agent_est.strftime('%Y-%m-%d %H:%M %Z')} (EST/EDT)")

        logger.info(f"🕚 Daily learning: 11:00 PM UTC (updates weights)")
        logger.info("")
        
        try:
            check_count = 0
            est_tz = pytz.timezone('America/New_York')
            logger.info("🔄 Entering main loop...")  # DEBUG: confirm we enter the loop
            first_iteration = True
            while True:
                # Get current time in UTC (Render uses UTC)
                current_time = datetime.now(pytz.UTC)
                check_count += 1

                # Log every 5 checks (every 5 minutes with 60s interval)
                if check_count % 5 == 1:
                    current_time_est = current_time.astimezone(est_tz)
                    logger.info(f"🔄 Loop check #{check_count} - {current_time_est.strftime('%H:%M:%S %Z')}")
                else:
                    logger.debug(f"Loop check #{check_count}...")
                
                # Log status every STATUS_LOG_INTERVAL checks
                if check_count % self.STATUS_LOG_INTERVAL == 0:
                    logger.info(f"\n=== Status Check #{check_count} ===")
                    # Show time in EST
                    current_time_est = current_time.astimezone(est_tz)
                    logger.info(f"Current time: {current_time_est.strftime('%H:%M:%S %Z')} (EST/EDT)")
                    logger.info(f"Active opportunities: {len(self.opportunities)}")
                    logger.info(f"LLM Weights: {self._format_weights()}")
                    if next_analysis:
                        # Ensure both times are timezone-aware for calculation
                        if next_analysis.tzinfo is None:
                            next_analysis_utc = pytz.UTC.localize(next_analysis)
                        else:
                            next_analysis_utc = next_analysis
                        time_until = (next_analysis_utc - current_time).total_seconds() / 60
                        if time_until > 0:
                            next_analysis_est = next_analysis_utc.astimezone(est_tz)
                            logger.info(f"Next analysis at: {next_analysis_est.strftime('%H:%M %Z')} (in {int(time_until)} minutes)")
                
                # Check for daily learning time (11pm UTC)
                if should_run_learning():
                    if (self.last_learning_check is None or
                        (current_time - self.last_learning_check).total_seconds() > self.LEARNING_CHECK_INTERVAL):
                        logger.info("\n" + "="*80)
                        logger.info("🧠 DAILY LEARNING TIME (11pm UTC)")
                        logger.info("="*80)
                        try:
                            run_daily_learning()
                            # Reload weights after learning completes
                            self.llm_weights = self._load_llm_weights()
                            logger.info(f"✅ Weights updated: {self._format_weights()}")
                        except Exception as e:
                            logger.error(f"❌ Learning failed: {e}", exc_info=True)
                        self.last_learning_check = current_time
                
                # Periodically reload weights (every hour) to pick up changes from evaluations
                if self.last_weight_reload is None or (current_time - self.last_weight_reload).total_seconds() > self.WEIGHT_RELOAD_INTERVAL:
                    old_weights = self.llm_weights.copy() if self.llm_weights else {}
                    self.llm_weights = self._load_llm_weights()
                    if old_weights != self.llm_weights:
                        logger.info(f"🔄 Weights reloaded: {self._format_weights()}")
                    self.last_weight_reload = current_time

                # Check if scheduled analysis time (skip first iteration to let service stabilize)
                if not first_iteration and self._should_run_analysis(current_time):
                    # Show time in EST for logging
                    current_time_est = current_time.astimezone(est_tz)
                    logger.info(f"\n{'='*80}")
                    logger.info(f"=== Scheduled Analysis Time: {current_time_est.strftime('%Y-%m-%d %H:%M:%S %Z')} (EST/EDT) ===")
                    logger.info(f"{'='*80}")
                    try:
                        self._run_full_analysis_with_rl()
                        logger.info(f"✅ Analysis completed successfully at {current_time_est.strftime('%H:%M:%S %Z')}")
                    except Exception as e:
                        logger.error(f"❌ Analysis failed at {current_time_est.strftime('%H:%M:%S %Z')}: {e}", exc_info=True)
                    self.last_analysis_time = current_time
                    # Update next analysis time
                    next_analysis = self.scheduler.get_next_analysis_time()

                # Check if scheduled agent workflow time (5:30 PM EST)
                if self._should_run_agents(current_time):
                    current_time_est = current_time.astimezone(est_tz)
                    logger.info(f"\n{'='*80}")
                    logger.info(f"=== Multi-Agent Workflow Time: {current_time_est.strftime('%Y-%m-%d %H:%M:%S %Z')} (EST/EDT) ===")
                    logger.info(f"{'='*80}")
                    try:
                        self._run_agents(current_time)
                        logger.info(f"✅ Agent workflow completed at {current_time_est.strftime('%H:%M:%S %Z')}")
                    except Exception as e:
                        logger.error(f"❌ Agent workflow failed at {current_time_est.strftime('%H:%M:%S %Z')}: {e}", exc_info=True)
                    self.last_agent_run_time = current_time

                # Check entry points continuously
                self._check_entry_points()

                # Mark first iteration as complete
                if first_iteration:
                    first_iteration = False
                    logger.info("✅ Main loop stabilized, analysis enabled for next iteration")

                # Wait before next check
                logger.debug(f"⏳ Sleeping for {self.check_interval}s before next check...")
                time.sleep(self.check_interval)
                logger.debug(f"⏱️ Sleep complete, resuming checks...")
                
        except KeyboardInterrupt:
            logger.info("\n⚠️  System stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            raise
    
    def _run_full_analysis_with_rl(self):
        """Run full analysis workflow WITH RL integration"""
        logger.info("Starting analysis workflow with RL integration...")
        
        try:
            # Steps 1-4: Same as before (get data, analyze with LLMs, synthesize)
            logger.info("Step 1: Reading data from Google Drive...")
            if not self.drive_reader.enabled:
                logger.error("Drive reader not enabled")
                return
            
            files = self.drive_reader.get_latest_analysis_files(pattern='summary')
            if not files:
                files = self.drive_reader.get_latest_analysis_files(pattern='report')
            
            if not files:
                logger.warning("No files found")
                return
            
            downloaded_files = []
            for file_info in files[:3]:
                file_path = self.drive_reader.download_file(file_info['id'], file_info['title'])
                if file_path:
                    downloaded_files.append(file_path)
            
            if not downloaded_files:
                logger.error("Failed to download files")
                return
            
            logger.info(f"Downloaded {len(downloaded_files)} files")
            
            logger.info("Step 2: Formatting data for LLMs...")
            data_summary = self.data_formatter.format_files(downloaded_files)
            
            logger.info("Step 3: Running LLM analysis...")
            current_datetime = datetime.now(pytz.UTC)
            llm_recommendations = self.llm_analyzer.analyze_all(data_summary, current_datetime)
            
            # Get current live prices for synthesis
            logger.info("Step 3.5: Fetching current live prices...")
            current_prices = self._get_current_prices_for_synthesis()
            if current_prices:
                logger.info(f"✅ Fetched {len(current_prices)} current prices for synthesis")
            else:
                logger.warning("⚠️ Could not fetch current prices - synthesis will proceed without live price context")
            
            logger.info("Step 4: Synthesizing with Gemini...")
            gemini_final = self.gemini_synthesizer.synthesize(llm_recommendations, current_datetime, current_prices)
            
            # NEW Step 5: Enhance with RL insights
            logger.info("Step 5 (NEW): Enhancing recommendations with RL insights...")
            enhanced_recommendations = self._enhance_with_rl(
                llm_recommendations,
                gemini_final
            )
            
            # Step 6: Send enhanced email
            logger.info("Step 6: Sending enhanced recommendations email...")
            self.email_sender.send_recommendations(
                llm_recommendations,
                enhanced_recommendations['final_text']
            )
            
            # NEW Step 7: Log recommendations to RL database (ALL LLM sources)
            logger.info("Step 7 (NEW): Logging recommendations to RL database...")
            
            recommendations_logged = 0
            recommendations_deduplicated = 0  # Renamed from recommendations_rejected to clarify these are duplicates, not actual failures
            recommendations_unrealistic = 0
            timestamp_str = current_datetime.isoformat()
            filename = f"analysis_{current_datetime.strftime('%Y%m%d_%H%M%S')}.txt"
            
            # Log individual LLM recommendations (ChatGPT, Gemini, Claude)
            for llm_name in ['chatgpt', 'gemini', 'claude']:
                if llm_name in llm_recommendations and llm_recommendations[llm_name]:
                    try:
                        # Parse LLM recommendations using RL parser
                        recs = self.rl_parser.parse_text(
                            llm_recommendations[llm_name],
                            llm_name.upper(),
                            timestamp_str,
                            filename
                        )
                        
                        # Post-process to correct current prices with live data
                        recs = self._post_process_recommendation_prices(recs, current_prices)
                        
                        for rec in recs:
                            try:
                                rec_id = self.rl_db.log_recommendation(rec)
                                if rec_id:
                                    recommendations_logged += 1
                                    # Check if it was marked as unrealistic
                                    if rec.get('confidence') == 'UNREALISTIC':
                                        recommendations_unrealistic += 1
                                    logger.debug(f"✅ Logged {llm_name} recommendation: {rec.get('pair')} {rec.get('direction')}")
                                else:
                                    recommendations_deduplicated += 1
                            except Exception as e:
                                logger.error(f"Error logging {llm_name} recommendation: {e}", exc_info=True)
                                recommendations_deduplicated += 1
                    except Exception as e:
                        logger.error(f"Error parsing {llm_name} recommendations: {e}", exc_info=True)
            
            # Log synthesis recommendations (Gemini Final)
            if gemini_final:
                try:
                    # Parse gemini_final using RL parser (same format as individual LLMs)
                    recs = self.rl_parser.parse_text(
                        gemini_final,
                        'SYNTHESIS',
                        timestamp_str,
                        filename
                    )
                    
                    # Post-process to correct current prices with live data
                    recs = self._post_process_recommendation_prices(recs, current_prices)
                    
                    for rec in recs:
                        try:
                            rec_id = self.rl_db.log_recommendation(rec)
                            if rec_id:
                                recommendations_logged += 1
                                # Check if it was marked as unrealistic
                                if rec.get('confidence') == 'UNREALISTIC':
                                    recommendations_unrealistic += 1
                                logger.debug(f"✅ Logged synthesis recommendation: {rec.get('pair')} {rec.get('direction')}")
                            else:
                                recommendations_deduplicated += 1
                        except Exception as e:
                            logger.error(f"Error logging synthesis recommendation: {e}", exc_info=True)
                            recommendations_deduplicated += 1
                except Exception as e:
                    logger.error(f"Error parsing synthesis recommendations: {e}", exc_info=True)
            
            logger.info(f"✅ Logged {recommendations_logged} recommendations for future learning (deduplicated: {recommendations_deduplicated}, unrealistic: {recommendations_unrealistic})")
            
            # Step 8: Extract entry/exit points from ALL LLMs (not just synthesis)
            logger.info("Step 8: Extracting entry/exit points from all LLMs...")
            
            # Parse opportunities from each LLM
            all_opportunities = {}
            
            # Parse from individual LLMs
            for llm_name in ['chatgpt', 'gemini', 'claude', 'deepseek']:
                if llm_name in llm_recommendations and llm_recommendations[llm_name]:
                    logger.info(f"   Parsing {llm_name.upper()} recommendations...")
                    opps = self.parser.parse_text(llm_recommendations[llm_name])
                    if opps:
                        # Post-process to correct current prices with live data
                        opps = self._post_process_current_prices(opps, current_prices)
                        all_opportunities[llm_name] = opps
                        pairs_str = ", ".join(o.get("pair", "") for o in opps if o.get("pair"))
                        logger.info(f"   Parsed {llm_name.upper()}: {len(opps)} opportunities, pairs: [{pairs_str}]")
                    else:
                        text_len = len((llm_recommendations[llm_name] or "").strip())
                        if text_len > 100:
                            logger.debug(f"   {llm_name.upper()}: 0 opportunities (parser may not match format). Preview: {(llm_recommendations[llm_name])[:300]}...")
                        # consol-recommend4 Phase 2.3: visibility when DeepSeek returns 0 (narrative vs JSON)
                        if llm_name == 'deepseek' and text_len > 50:
                            logger.info(
                                "   DeepSeek: 0 opportunities parsed. If DeepSeek output format differs (narrative vs JSON), "
                                "request MACHINE_READABLE JSON in the prompt or see Scalp-Engine USER_GUIDE §13."
                            )
            
            # Parse from synthesis (Gemini Final)
            if gemini_final:
                logger.info("   Parsing SYNTHESIS recommendations...")
                synthesis_opps = self.parser.parse_text(gemini_final)
                if synthesis_opps:
                    # Post-process to correct current prices with live data
                    synthesis_opps = self._post_process_current_prices(synthesis_opps, current_prices)
                    all_opportunities['synthesis'] = synthesis_opps
                    pairs_str = ", ".join(o.get("pair", "") for o in synthesis_opps if o.get("pair"))
                    logger.info(f"   Parsed SYNTHESIS: {len(synthesis_opps)} opportunities, pairs: [{pairs_str}]")
            
            # Fill missing entry prices (from current_prices or synthesis) so merge does not drop opps
            if all_opportunities:
                self._fill_missing_entry_prices(all_opportunities, current_prices)
            
            # Merge all opportunities: keep unique pairs, select best entry price
            if all_opportunities:
                bridge = MarketBridge()
                merged_opportunities = bridge.merge_opportunities_from_all_llms(all_opportunities)
                if merged_opportunities:
                    logger.info(f"✅ Merged {len(merged_opportunities)} unique opportunities from all LLMs")
                    self.opportunities = merged_opportunities
                else:
                    logger.warning("⚠️ No opportunities found after merging")
            else:
                logger.warning("⚠️ No LLM recommendations available to parse")
            
            # NEW Step 9: Export Market State for Scalp-Engine (with consensus and LLM weights)
            logger.info("Step 9 (NEW): Exporting market state for Scalp-Engine...")
            try:
                bridge = MarketBridge()
                exported_state = bridge.export_market_state(
                    self.opportunities, 
                    gemini_final,
                    llm_weights=self.llm_weights,  # Pass LLM weights for auto-trader
                    llm_recommendations=llm_recommendations,  # Pass individual LLM recommendations for accurate consensus
                    all_opportunities=all_opportunities  # Pass parsed opportunities for reliable consensus calculation
                )
                if exported_state:
                    logger.info("✅ Market state exported for Scalp-Engine")
                    logger.info(f"   Exported state: {len(self.opportunities)} opportunities, "
                              f"bias={exported_state.get('global_bias')}, regime={exported_state.get('regime')}")
                else:
                    logger.error("❌ Market state export returned None - file may not have been written")
            except Exception as e:
                logger.error(f"❌ Failed to export market state: {e}", exc_info=True)
                logger.error("   Scalp-Engine will not be able to access market state until next analysis")
            
            logger.info("✅ Full analysis workflow completed")
            
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}", exc_info=True)
    
    def _get_current_prices_for_synthesis(self) -> Dict[str, float]:
        """
        Get current live prices for major currency pairs to pass to synthesizer
        
        Returns:
            Dictionary mapping currency pairs to current prices (e.g., {'EUR/USD': 1.0850})
        """
        if not self.price_monitor:
            logger.warning("PriceMonitor not available - cannot fetch current prices")
            return {}
        
        # Major currency pairs to track
        pairs = [
            'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD',
            'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'EUR/AUD',
            'EUR/CAD', 'GBP/AUD', 'GBP/CAD', 'AUD/NZD', 'CAD/CHF', 'EUR/CHF',
            'GBP/CHF', 'AUD/CHF', 'NZD/CHF', 'CAD/JPY', 'CHF/JPY', 'NZD/JPY',
            'USD/ZAR', 'USD/MXN'
        ]
        
        current_prices = {}
        for pair in pairs:
            try:
                rate = self.price_monitor.get_rate(pair)
                if rate:
                    current_prices[pair] = rate
            except Exception as e:
                logger.debug(f"Could not fetch price for {pair}: {e}")
                continue
        
        return current_prices
    
    def _post_process_current_prices(self, opportunities: List[Dict], current_prices: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        Post-process opportunities to correct/update current prices with live data
        
        Args:
            opportunities: List of opportunity dictionaries
            current_prices: Dictionary of current live prices (if None, will fetch)
            
        Returns:
            List of opportunities with corrected current prices
        """
        if not current_prices:
            current_prices = self._get_current_prices_for_synthesis()
        
        if not current_prices:
            logger.warning("⚠️ No current prices available for post-processing")
            return opportunities
        
        corrected_count = 0
        for opp in opportunities:
            pair = opp.get('pair')
            if not pair:
                continue
            
            # Normalize pair format
            if '/' not in pair:
                # Convert GBPUSD -> GBP/USD
                if len(pair) == 6:
                    pair_normalized = f"{pair[:3]}/{pair[3:]}"
                else:
                    continue
            else:
                pair_normalized = pair
            
            # Get live price
            live_price = current_prices.get(pair_normalized)
            if live_price:
                # Check if opportunity has a current_price field
                if 'current_price' in opp:
                    old_price = opp['current_price']
                    # Validate both prices are numeric before calculating difference
                    if not isinstance(old_price, (int, float)) or not isinstance(live_price, (int, float)):
                        logger.warning(
                            f"Invalid price types for {pair_normalized}: "
                            f"old={type(old_price).__name__}, live={type(live_price).__name__} — updating directly"
                        )
                        opp['current_price'] = live_price
                        continue
                    # Calculate difference
                    pip_value = 0.01 if 'JPY' in pair_normalized else 0.0001
                    diff_pips = abs(live_price - old_price) / pip_value
                    diff_percent = abs((live_price - old_price) / old_price * 100) if old_price else 0
                    
                    # If difference is significant (> 0.1% or > 10 pips), correct it
                    if diff_percent > 0.1 or diff_pips > 10:
                        logger.info(
                            f"🔧 Correcting current price for {pair}: "
                            f"{old_price:.5f} → {live_price:.5f} "
                            f"(diff: {diff_pips:.1f} pips, {diff_percent:.2f}%)"
                        )
                        opp['current_price'] = live_price
                        corrected_count += 1
                    else:
                        # Update anyway to ensure accuracy
                        opp['current_price'] = live_price
                else:
                    # Add current_price if missing
                    opp['current_price'] = live_price
        
        if corrected_count > 0:
            logger.info(f"✅ Corrected current prices for {corrected_count} opportunities")
        
        return opportunities
    
    def _fill_missing_entry_prices(
        self,
        all_opportunities: Dict[str, List[Dict]],
        current_prices: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Fill missing entry prices in all_opportunities. For each opp with entry None or <= 0:
        use current_prices[pair], else synthesis opp with same (pair, direction), else remove and log.
        Modifies all_opportunities in place.
        """
        if not current_prices:
            current_prices = self._get_current_prices_for_synthesis()
        synthesis_opps = all_opportunities.get('synthesis') or []
        synthesis_by_key = {}
        for o in synthesis_opps:
            p = (o.get('pair', '').upper(), (o.get('direction') or '').upper())
            if p[0] and p[1] and o.get('entry'):
                synthesis_by_key[p] = o['entry']
        
        filled_from_price = 0
        filled_from_synthesis = 0
        dropped = 0
        for llm_name, opps in list(all_opportunities.items()):
            to_keep = []
            for opp in opps:
                entry = opp.get('entry') or 0.0
                if entry > 0:
                    to_keep.append(opp)
                    continue
                pair = opp.get('pair', '')
                direction = (opp.get('direction') or '').upper()
                if not pair or not direction:
                    dropped += 1
                    logger.debug(f"Dropped opp (no pair/direction) from {llm_name}")
                    continue
                # Normalize pair: try multiple formats if initial normalization fails
                pair_norm = pair if '/' in pair else f"{pair[:3]}/{pair[3:]}" if len(pair) >= 6 else pair
                pair_upper = pair_norm.upper()

                # Try to find entry price from current_prices (try multiple formats for robustness)
                entry_from_price = None
                current_prices_keys = [k.upper() for k in (current_prices or {}).keys()]

                # Try exact match with current_prices
                if current_prices:
                    for test_pair in [pair_norm, pair_norm.upper(), pair_norm.replace('/', ''), pair_norm.replace('/', '').upper()]:
                        for price_key in current_prices:
                            if price_key.upper() == test_pair.upper():
                                entry_from_price = float(current_prices[price_key])
                                break
                        if entry_from_price:
                            break

                key = (pair_upper, direction)
                if entry_from_price:
                    opp['entry'] = entry_from_price
                    filled_from_price += 1
                    logger.debug(f"Filled missing entry for {pair_norm} {direction} from current price (source: {llm_name})")
                    to_keep.append(opp)
                elif key in synthesis_by_key:
                    opp['entry'] = float(synthesis_by_key[key])
                    filled_from_synthesis += 1
                    logger.debug(f"Filled missing entry for {pair_norm} {direction} from synthesis (source: {llm_name})")
                    to_keep.append(opp)
                else:
                    dropped += 1
                    logger.warning(f"⚠️ DROPPED opportunity {pair_norm} {direction}: no entry price and no fallback available (source: {llm_name})")
            all_opportunities[llm_name] = to_keep
        if filled_from_price or filled_from_synthesis or dropped:
            logger.info(
                f"📋 Fill missing entry: {filled_from_price} from current price, "
                f"{filled_from_synthesis} from synthesis, {dropped} dropped"
            )
    
    def _post_process_recommendation_prices(self, recommendations: List[Dict], current_prices: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        Post-process recommendations to correct/update current prices with live data
        
        Args:
            recommendations: List of recommendation dictionaries (RL format)
            current_prices: Dictionary of current live prices (if None, will fetch)
            
        Returns:
            List of recommendations with corrected current prices
        """
        if not current_prices:
            current_prices = self._get_current_prices_for_synthesis()
        
        if not current_prices:
            logger.warning("⚠️ No current prices available for post-processing")
            return recommendations
        
        corrected_count = 0
        for rec in recommendations:
            pair = rec.get('pair', '')
            if not pair:
                continue
            
            # Normalize pair format (RL format may have no slash)
            if '/' not in pair:
                # Convert GBPUSD -> GBP/USD
                if len(pair) == 6:
                    pair_normalized = f"{pair[:3]}/{pair[3:]}"
                else:
                    continue
            else:
                pair_normalized = pair
            
            # Get live price
            live_price = current_prices.get(pair_normalized)
            if live_price:
                # Check if recommendation has a current_price field
                if 'current_price' in rec:
                    old_price = rec['current_price']
                    # Calculate difference
                    pip_value = 0.01 if 'JPY' in pair_normalized else 0.0001
                    diff_pips = abs(live_price - old_price) / pip_value
                    diff_percent = abs((live_price - old_price) / old_price * 100) if old_price else 0
                    
                    # If difference is significant (> 0.1% or > 10 pips), correct it
                    if diff_percent > 0.1 or diff_pips > 10:
                        logger.info(
                            f"🔧 Correcting current price for {pair}: "
                            f"{old_price:.5f} → {live_price:.5f} "
                            f"(diff: {diff_pips:.1f} pips, {diff_percent:.2f}%)"
                        )
                        rec['current_price'] = live_price
                        corrected_count += 1
                    else:
                        # Update anyway to ensure accuracy
                        rec['current_price'] = live_price
                else:
                    # Add current_price if missing
                    rec['current_price'] = live_price
        
        if corrected_count > 0:
            logger.info(f"✅ Corrected current prices for {corrected_count} recommendations")
        
        return recommendations
    
    def _enhance_with_rl(self, llm_recommendations: dict, gemini_final: str) -> dict:
        """Enhance recommendations with RL insights"""
        
        # Generate performance report
        report = self.learning_engine.generate_performance_report()
        
        # Build enhancement text
        enhancement = "\n\n" + "="*80 + "\n"
        enhancement += "🧠 MACHINE LEARNING INSIGHTS (Based on Historical Performance)\n"
        enhancement += "="*80 + "\n\n"
        
        enhancement += "📊 LLM Performance Weights (Based on Past Accuracy):\n"
        for llm, weight in self.llm_weights.items():
            # Always show weight, even if no stats in report
            if llm in report.get('llm_performance', {}):
                stats = report['llm_performance'][llm]
                enhancement += f"  • {llm.upper()}: {weight*100:.0f}% weight "
                enhancement += f"(Win Rate: {stats.get('win_rate', 0)*100:.0f}%, "
                enhancement += f"Avg P&L: {stats.get('avg_pnl', 0):.0f} pips)\n"
            else:
                # Show weight even if no performance stats available
                enhancement += f"  • {llm.upper()}: {weight*100:.0f}% weight\n"
        
        enhancement += "\n"
        
        # Consensus insights
        if 'consensus_analysis' in report and report['consensus_analysis']:
            enhancement += "🎯 Consensus Analysis:\n"
            for consensus_type, stats in report['consensus_analysis'].items():
                if stats['sample_size'] > 0:
                    enhancement += f"  • {consensus_type}: {stats['win_rate']*100:.0f}% win rate "
                    enhancement += f"({stats['sample_size']} historical trades)\n"
            enhancement += "\n"
        
        # Best LLM
        if self.llm_weights:
            best_llm = max(self.llm_weights, key=self.llm_weights.get)
            enhancement += f"🏆 Highest Accuracy: {best_llm.upper()} "
            enhancement += f"({self.llm_weights[best_llm]*100:.0f}% confidence weight)\n\n"
        
        # Recommendation
        enhancement += "💡 Recommendation:\n"
        enhancement += "  Based on historical performance, prioritize trades where:\n"
        if self.llm_weights:
            best_llm = max(self.llm_weights, key=self.llm_weights.get)
            enhancement += f"  1. {best_llm.upper()} agrees (highest accuracy)\n"
        enhancement += "  2. All 3 LLMs agree (best win rate)\n"
        enhancement += "  3. Consider reducing position size when LLMs disagree\n"
        
        enhancement += "\n" + "="*80 + "\n"
        
        # Combine with original synthesis (handle None case)
        if gemini_final:
            enhanced_final = gemini_final + enhancement
        else:
            # If synthesis failed, just return the enhancement as the final text
            enhanced_final = "⚠️ No LLM recommendations were generated. RL insights only:\n" + enhancement
        
        return {
            'final_text': enhanced_final,
            'weights': self.llm_weights,
            'report': report
        }
    
    def _convert_opportunity_to_recommendation(self, opportunity: dict, timestamp: datetime, llm_source: str = 'synthesis') -> dict:
        """
        Convert Step 5/8 opportunity format to Step 7 recommendation format
        
        Step 5/8 format:
        {
            'pair': 'GBP/USD',
            'entry': 1.2650,
            'exit': None,
            'stop_loss': 1.2600,
            'direction': 'BUY' or 'SELL',
            'position_size': None,
            'timeframe': 'INTRADAY',
            'recommendation': '...',
            'source': 'text_parsing'
        }
        
        Step 7 format:
        {
            'timestamp': '2026-01-12T03:06:00',
            'date_generated': '2026-01-12',
            'llm_source': 'synthesis',
            'pair': 'GBPUSD',  # No slash
            'direction': 'LONG' or 'SHORT',
            'entry_price': 1.2650,
            'stop_loss': 1.2600,
            'take_profit_1': None,
            'take_profit_2': None,
            'position_size_pct': 2.0,
            'confidence': None,
            'rationale': '...',
            'timeframe': 'INTRADAY',
            'source_file': ''
        }
        """
        # Convert pair format: GBP/USD -> GBPUSD
        pair = opportunity.get('pair', '').replace('/', '').replace('-', '').upper()
        
        # Convert direction: BUY -> LONG, SELL -> SHORT
        direction = opportunity.get('direction', '').upper()
        if direction in ['BUY', 'LONG']:
            direction = 'LONG'
        elif direction in ['SELL', 'SHORT']:
            direction = 'SHORT'
        else:
            direction = 'LONG'  # Default
        
        # Extract exit price as take_profit_1 if available
        tp1 = opportunity.get('exit')
        
        # Convert position_size to position_size_pct (default 2.0)
        position_size = opportunity.get('position_size')
        position_size_pct = 2.0  # Default
        if position_size:
            try:
                # If it's a string with %, extract the number
                if isinstance(position_size, str) and '%' in position_size:
                    position_size_pct = float(position_size.replace('%', '').strip())
                else:
                    position_size_pct = float(position_size)
            except (ValueError, TypeError):
                position_size_pct = 2.0
        
        timestamp_str = timestamp.isoformat()
        
        return {
            'timestamp': timestamp_str,
            'date_generated': timestamp_str.split('T')[0],
            'llm_source': llm_source.lower(),
            'pair': pair,
            'direction': direction,
            'entry_price': opportunity.get('entry'),
            'stop_loss': opportunity.get('stop_loss'),
            'take_profit_1': tp1,
            'take_profit_2': None,  # Step 5 doesn't extract TP2
            'position_size_pct': position_size_pct,
            'confidence': None,
            'rationale': opportunity.get('recommendation', '')[:500] if opportunity.get('recommendation') else '',
            'timeframe': opportunity.get('timeframe', 'INTRADAY'),
            'source_file': ''
        }
    
    def _save_recommendations_to_file(self, llm_recs: dict, gemini_final: str, timestamp: datetime) -> str:
        """Save recommendations to file in both .txt and .json formats for RL"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs('data/recommendations', exist_ok=True)
            
            # Generate filenames
            base_name = f"forex_recommendations_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            txt_filename = f"data/recommendations/{base_name}.txt"
            json_filename = f"data/recommendations/{base_name}.json"
            
            # Save as .txt (human-readable format)
            content = "="*80 + "\n"
            content += "FOREX TRADING RECOMMENDATIONS\n"
            content += f"Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += "="*80 + "\n\n"
            
            # Add each LLM section
            for llm_name in ['chatgpt', 'gemini', 'claude']:
                if llm_name in llm_recs:
                    content += "\n" + "="*80 + "\n"
                    content += f"{llm_name.upper()} RECOMMENDATIONS\n"
                    content += "="*80 + "\n\n"
                    content += llm_recs[llm_name] + "\n"
            
            # Add synthesis
            content += "\n" + "="*80 + "\n"
            content += "GEMINI FINAL RECOMMENDATION\n"
            content += "="*80 + "\n\n"
            content += gemini_final + "\n"
            
            content += "\n" + "="*80 + "\n"
            content += "End of Recommendations\n"
            content += "="*80 + "\n"
            
            # Write .txt file
            with open(txt_filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Save as .json (structured format for easier parsing)
            json_data = {
                'timestamp': timestamp.isoformat(),
                'date_generated': timestamp.strftime('%Y-%m-%d'),
                'llm_recommendations': llm_recs,
                'gemini_final': gemini_final,
                'recommendations': []  # Will be populated by parser
            }
            
            # Write .json file
            import json
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved recommendations to: {txt_filename} and {json_filename}")
            return json_filename  # Return .json for better parsing (RL parser handles JSON better)
            
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}", exc_info=True)
            return None
    
    def _check_entry_points(self):
        """Check all opportunities for entry points with dynamic ATR-based tolerance"""
        if not self.opportunities:
            return
        
        logger.debug(f"Checking {len(self.opportunities)} opportunities...")
        
        for opp in self.opportunities:
            try:
                pair = opp.get('pair')
                entry = opp.get('entry')
                direction = opp.get('direction')

                if not pair or not direction:
                    logger.warning(f"Skipping incomplete opportunity (missing pair or direction): {opp}")
                    continue
                if entry is None:
                    logger.debug(f"Skipping {pair} {direction}: no entry price set")
                    continue

                # Skip if already alerted
                if self.alert_history.has_alerted(opp):
                    continue
                
                # Get current price
                current_price = self.price_monitor.get_rate(pair)
                if not current_price:
                    logger.warning(f"Skipping opportunity for {pair}: price data unavailable")
                    continue
                
                # Extract confidence score from opportunity
                # Try multiple possible fields and convert to 0.0-1.0 scale
                confidence_score = 0.75  # Default
                if 'confidence' in opp:
                    conf_str = str(opp['confidence']).lower()
                    if 'high' in conf_str or 'strong' in conf_str:
                        confidence_score = 0.85
                    elif 'medium' in conf_str:
                        confidence_score = 0.75
                    elif 'low' in conf_str:
                        confidence_score = 0.65
                    else:
                        # Try to parse as number
                        try:
                            conf_val = float(opp['confidence'])
                            if 0 <= conf_val <= 1:
                                confidence_score = conf_val
                            elif 0 <= conf_val <= 100:
                                confidence_score = conf_val / 100.0
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Could not parse confidence value '{opp.get('confidence')}': {e}")
                
                # Also check if we can get confidence from LLM weights
                # If this opportunity came from a specific LLM with high weight, boost confidence
                if 'llm_source' in opp:
                    llm_source = opp['llm_source'].lower()
                    if llm_source in self.llm_weights:
                        # Use LLM weight as additional confidence signal
                        llm_weight = self.llm_weights[llm_source]
                        # Blend: 70% from explicit confidence, 30% from LLM weight
                        confidence_score = (confidence_score * 0.7) + (llm_weight * 0.3)
                
                # Extract timeframe classification (default to INTRADAY if not specified)
                timeframe = opp.get('timeframe', 'INTRADAY')
                if isinstance(timeframe, str):
                    timeframe = timeframe.upper()
                    if timeframe not in ['INTRADAY', 'SWING']:
                        timeframe = 'INTRADAY'  # Default to INTRADAY if invalid
                else:
                    timeframe = 'INTRADAY'
                
                # Check if entry point is hit with dynamic ATR-based tolerance
                # Pass confidence_score and timeframe to enable different rules for different trade types
                hit = self.price_monitor.check_entry_point(
                    pair=pair,
                    entry_price=entry,
                    direction=direction,
                    confidence_score=confidence_score,
                    timeframe=timeframe
                )
                
                if hit:
                    # Throttle: first hit per (pair, direction) in window at INFO, subsequent at DEBUG (consol-recommend2 Phase 1.5)
                    key = (pair, direction)
                    now_ts = time.time()
                    last_ts = self._entry_point_hit_last_logged.get(key, 0)
                    if now_ts - last_ts >= self._entry_point_hit_window_seconds:
                        logger.info(
                            f"🚨 ENTRY POINT HIT: {pair} {direction} @ {entry} "
                            f"({timeframe}, confidence: {confidence_score:.2f}, ATR-based tolerance)"
                        )
                        self._entry_point_hit_last_logged[key] = now_ts
                    else:
                        logger.debug(
                            f"🚨 ENTRY POINT HIT: {pair} {direction} @ {entry} "
                            f"({timeframe}, throttled)"
                        )

                    # Send alert
                    if self.alert_manager.send_entry_alert(opp, current_price):
                        self.alert_history.record_alert(opp, current_price)
                        logger.info(f"✅ Alert sent for {pair}")
                    
            except Exception as e:
                logger.error(f"Error checking opportunity {opp.get('pair', 'unknown')}: {e}", exc_info=True)

def main():
    """Main entry point"""
    system = TradeAlertSystem()
    system.run()

if __name__ == '__main__':
    main()
