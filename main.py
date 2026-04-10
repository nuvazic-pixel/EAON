#!/usr/bin/env python3
"""
EAON 2.0 — Entry Point
=======================
Emergent Autonomous Orchestration Network

Usage:
    python main.py                    # Interactive mode
    python main.py -p "your prompt"   # Single prompt
    python main.py --mode safe        # Set mode
    python main.py --stats            # Show stats
"""

import os
import sys
import argparse
from pathlib import Path

# Load .env before importing config
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv optional

from config import init_settings, get_settings, OrchestratorMode
from utils import setup_logging, get_logger
from core import Orchestrator


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="EAON 2.0 - Emergent Autonomous Orchestration Network",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                      Interactive REPL
  python main.py -p "Analyze threat"  Single prompt
  python main.py --mode safe          Start in safe mode
  python main.py --stats              Show system stats
        """,
    )
    
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        help="Single prompt to execute (non-interactive)",
    )
    
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["normal", "balanced", "safe", "lockdown"],
        default="normal",
        help="Operating mode (default: normal)",
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show system statistics and exit",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output logs in JSON format",
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    
    return parser.parse_args()


def show_banner() -> None:
    """Display EAON banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ███████╗ █████╗  ██████╗ ███╗   ██╗                    ║
    ║   ██╔════╝██╔══██╗██╔═══██╗████╗  ██║                    ║
    ║   █████╗  ███████║██║   ██║██╔██╗ ██║                    ║
    ║   ██╔══╝  ██╔══██║██║   ██║██║╚██╗██║                    ║
    ║   ███████╗██║  ██║╚██████╔╝██║ ╚████║                    ║
    ║   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝                    ║
    ║                                                           ║
    ║   Emergent Autonomous Orchestration Network v2.0          ║
    ║   ─────────────────────────────────────────────────────   ║
    ║   Type 'help' for commands, 'exit' to quit                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def show_help() -> None:
    """Display help text."""
    help_text = """
    EAON Commands:
    ─────────────────────────────────────────
    help          Show this help
    exit / quit   Exit EAON
    stats         Show system statistics
    mode <name>   Change mode (normal/balanced/safe/lockdown)
    cache         Show cache statistics
    clear         Clear screen
    
    Any other input is processed as a prompt.
    """
    print(help_text)


def interactive_loop(orchestrator: Orchestrator, logger) -> None:
    """Run interactive REPL loop."""
    show_banner()
    
    while True:
        try:
            prompt = input("\n[EAON] > ").strip()
            
            if not prompt:
                continue
            
            # Handle commands
            cmd = prompt.lower()
            
            if cmd in ("exit", "quit", "q"):
                print("\n[EAON] Shutting down...")
                break
            
            elif cmd == "help":
                show_help()
                continue
            
            elif cmd == "stats":
                stats = orchestrator.get_stats()
                print("\n[EAON] System Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                continue
            
            elif cmd == "cache":
                from adapters import cache_stats
                stats = cache_stats()
                print("\n[EAON] Cache Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                continue
            
            elif cmd.startswith("mode "):
                new_mode = cmd.split()[1]
                if new_mode in ("normal", "balanced", "safe", "lockdown"):
                    orchestrator.set_mode(new_mode, reason="user command")
                    print(f"[EAON] Mode changed to: {new_mode}")
                else:
                    print(f"[EAON] Invalid mode: {new_mode}")
                continue
            
            elif cmd == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                show_banner()
                continue
            
            # Process as prompt
            print("\n[EAON] Processing...")
            decision, report = orchestrator.run(prompt)
            
            # Display result
            print(f"\n[EAON] Intent: {decision.intent} | Model: {decision.model} | Mode: {decision.mode}")
            
            if report.ok:
                print(f"\n{report.output_text}")
                print(f"\n[{report.model_used}] {report.inference_time_ms:.0f}ms")
            else:
                print(f"\n[ERROR] {report.error}")
        
        except KeyboardInterrupt:
            print("\n\n[EAON] Interrupted. Type 'exit' to quit.")
            continue
        
        except EOFError:
            print("\n[EAON] Shutting down...")
            break
        
        except Exception as e:
            logger.error("repl_error", error=str(e))
            print(f"\n[ERROR] {e}")


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Version
    if args.version:
        print("EAON 2.0.0")
        return 0
    
    # Initialize settings
    settings = init_settings()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else settings.log.level
    log_format = "json" if args.json_logs else settings.log.format
    
    setup_logging(
        level=log_level,
        format=log_format,
        log_file=settings.log.file_path,
        app_name=settings.app_name,
        version=settings.version,
    )
    
    logger = get_logger("main")
    logger.info("eaon_starting", mode=args.mode, version=settings.version)
    
    # Create orchestrator
    orchestrator = Orchestrator()
    
    # Set initial mode if specified
    if args.mode != "normal":
        orchestrator.set_mode(args.mode, reason="cli argument")
    
    # Stats only
    if args.stats:
        stats = orchestrator.get_stats()
        print("EAON System Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return 0
    
    # Single prompt mode
    if args.prompt:
        decision, report = orchestrator.run(args.prompt)
        
        if report.ok:
            print(report.output_text)
            return 0
        else:
            print(f"Error: {report.error}", file=sys.stderr)
            return 1
    
    # Interactive mode
    interactive_loop(orchestrator, logger)
    
    logger.info("eaon_shutdown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
