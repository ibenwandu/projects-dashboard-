#!/usr/bin/env python3
"""
GeminiAgent Verification Script

Quick verification that GeminiAgent initializes and integrates properly.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add src to path (following the pattern used in demo.py)
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        from agents import GeminiAgent, BaseAgent
        print("  [OK] GeminiAgent imported successfully")
        print(f"  [OK] GeminiAgent inherits from BaseAgent: {issubclass(GeminiAgent, BaseAgent)}")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """Test that GeminiAgent can be instantiated."""
    print("\nTesting GeminiAgent initialization...")
    try:
        from agents import GeminiAgent
        from utils.config import load_config

        config = load_config()
        gemini_config = config.get("sub_agents", {}).get("gemini", {})

        agent = GeminiAgent(
            name=gemini_config.get("name", "Gemini Agent"),
            config=gemini_config
        )

        print(f"  [OK] GeminiAgent created: {agent.name}")
        print(f"  [OK] Agent type: {agent.agent_type}")
        print(f"  [OK] Agent status: {agent.status.value}")
        print(f"  [OK] Gemini tool available: {agent.gemini is not None}")

        return True
    except Exception as e:
        print(f"  [FAIL] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ecosystem_integration():
    """Test that GeminiAgent integrates with the agent ecosystem."""
    print("\nTesting ecosystem integration...")
    try:
        import asyncio
        from main import AgentEcosystem

        async def check_integration():
            ecosystem = AgentEcosystem()
            print(f"  [OK] AgentEcosystem created")

            # Start ecosystem (this initializes all sub-agents)
            await ecosystem.start()
            print(f"  [OK] AgentEcosystem started")

            # Check if gemini agent was initialized
            if "gemini" in ecosystem.sub_agents:
                gemini_agent = ecosystem.sub_agents["gemini"]
                print(f"  [OK] GeminiAgent registered in ecosystem")
                print(f"  [OK] GeminiAgent name: {gemini_agent.name}")
                print(f"  [OK] Total sub-agents: {len(ecosystem.sub_agents)}")
                return True
            else:
                print(f"  [FAIL] GeminiAgent not found in ecosystem")
                print(f"  Available agents: {list(ecosystem.sub_agents.keys())}")
                return False

        return asyncio.run(check_integration())

    except Exception as e:
        print(f"  [FAIL] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("GeminiAgent Verification Suite")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Initialization": test_agent_initialization(),
        "Ecosystem Integration": test_ecosystem_integration(),
    }

    print("\n" + "=" * 60)
    print("Verification Results")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{test_name:<30} {status}")

    all_passed = all(results.values())
    print("=" * 60)

    if all_passed:
        print("[OK] All verification tests passed!")
        return 0
    else:
        print("[FAIL] Some tests failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
