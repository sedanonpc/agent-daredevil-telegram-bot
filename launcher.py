#!/usr/bin/env python3
"""
Telegram Bot & RAG Manager Launcher
===================================
This launcher starts both the Telegram bot and RAG Manager web interface simultaneously.

Author: Agent Daredevil
Repository: https://github.com/your-repo/telethon-rag-bot
"""

import subprocess
import threading
import time
import sys
import os
import webbrowser
from datetime import datetime
import signal
import atexit

# Configuration
STREAMLIT_PORT = 8501
RAG_MANAGER_SCRIPT = "rag_manager.py"
TELEGRAM_BOT_SCRIPT = "telegram_bot.py"

class Colors:
    """ANSI color codes for console output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ProcessManager:
    """Manages the subprocesses for both applications"""
    
    def __init__(self):
        self.streamlit_process = None
        self.telegram_process = None
        self.running = False
        
    def print_banner(self):
        """Print startup banner"""
        banner = f"""
{Colors.HEADER}{'='*70}
{Colors.BOLD}🤖 TELEGRAM BOT & RAG MANAGER LAUNCHER 🤖{Colors.ENDC}
{Colors.HEADER}{'='*70}{Colors.ENDC}

{Colors.OKCYAN}📋 What this launcher does:{Colors.ENDC}
{Colors.OKGREEN}✓{Colors.ENDC} Starts the RAG Manager web interface (Streamlit)
{Colors.OKGREEN}✓{Colors.ENDC} Starts the Telegram bot with OpenAI integration
{Colors.OKGREEN}✓{Colors.ENDC} Opens your web browser to the RAG Manager
{Colors.OKGREEN}✓{Colors.ENDC} Provides real-time console monitoring

{Colors.OKCYAN}🌐 RAG Manager:{Colors.ENDC} http://localhost:{STREAMLIT_PORT}
{Colors.OKCYAN}🤖 Bot Status:{Colors.ENDC} Will be shown below when started

{Colors.WARNING}💡 Tip:{Colors.ENDC} Keep this console open to monitor both services
{Colors.WARNING}🛑 Stop:{Colors.ENDC} Press Ctrl+C to stop both services

{Colors.HEADER}{'='*70}{Colors.ENDC}
"""
        print(banner)
    
    def check_dependencies(self):
        """Check if required files exist"""
        missing_files = []
        
        if not os.path.exists(RAG_MANAGER_SCRIPT):
            missing_files.append(RAG_MANAGER_SCRIPT)
        
        if not os.path.exists(TELEGRAM_BOT_SCRIPT):
            missing_files.append(TELEGRAM_BOT_SCRIPT)
        
        if missing_files:
            print(f"{Colors.FAIL}❌ Missing required files:{Colors.ENDC}")
            for file in missing_files:
                print(f"   - {file}")
            print(f"\n{Colors.WARNING}Please make sure you're running this from the correct directory.{Colors.ENDC}")
            return False
        
        return True
    
    def log_message(self, source, message, color=Colors.ENDC):
        """Log a message with timestamp and source"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.OKCYAN}[{timestamp}]{Colors.ENDC} {color}[{source}]{Colors.ENDC} {message}")
    
    def start_streamlit(self):
        """Start the Streamlit RAG Manager"""
        try:
            self.log_message("STREAMLIT", "Starting RAG Manager...", Colors.OKBLUE)
            
            # Start Streamlit process
            cmd = [sys.executable, "-m", "streamlit", "run", RAG_MANAGER_SCRIPT, 
                   "--server.port", str(STREAMLIT_PORT), 
                   "--server.headless", "true",
                   "--browser.gatherUsageStats", "false"]
            
            self.streamlit_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor Streamlit output
            def monitor_streamlit():
                for line in iter(self.streamlit_process.stdout.readline, ''):
                    if not self.running:
                        break
                    line = line.strip()
                    if line:
                        # Filter important messages
                        if "Local URL:" in line or "Network URL:" in line:
                            self.log_message("STREAMLIT", f"🌐 {line}", Colors.OKGREEN)
                        elif "Stopping..." in line or "error" in line.lower():
                            self.log_message("STREAMLIT", line, Colors.FAIL)
                        elif "You can now view your Streamlit app" in line:
                            self.log_message("STREAMLIT", "✅ RAG Manager is ready!", Colors.OKGREEN)
                            # Open browser after a short delay
                            threading.Timer(2.0, self.open_browser).start()
            
            threading.Thread(target=monitor_streamlit, daemon=True).start()
            
            # Wait a moment for Streamlit to start
            time.sleep(3)
            self.log_message("STREAMLIT", "✅ RAG Manager started successfully", Colors.OKGREEN)
            
        except Exception as e:
            self.log_message("STREAMLIT", f"❌ Failed to start: {e}", Colors.FAIL)
    
    def start_telegram_bot(self):
        """Start the Telegram bot"""
        try:
            self.log_message("TELEGRAM", "Starting Telegram bot...", Colors.OKBLUE)
            
            # Start Telegram bot process
            self.telegram_process = subprocess.Popen(
                [sys.executable, TELEGRAM_BOT_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor Telegram bot output
            def monitor_telegram():
                for line in iter(self.telegram_process.stdout.readline, ''):
                    if not self.running:
                        break
                    line = line.strip()
                    if line:
                        # Filter and colorize important messages
                        if "✅" in line or "started" in line.lower():
                            self.log_message("TELEGRAM", line, Colors.OKGREEN)
                        elif "❌" in line or "error" in line.lower():
                            self.log_message("TELEGRAM", line, Colors.FAIL)
                        elif "📨" in line or "🤖" in line:
                            self.log_message("TELEGRAM", line, Colors.OKCYAN)
                        elif "🚀" in line or "💬" in line or "🛑" in line:
                            self.log_message("TELEGRAM", line, Colors.WARNING)
                        else:
                            self.log_message("TELEGRAM", line)
            
            threading.Thread(target=monitor_telegram, daemon=True).start()
            
            time.sleep(2)
            self.log_message("TELEGRAM", "✅ Telegram bot process started", Colors.OKGREEN)
            
        except Exception as e:
            self.log_message("TELEGRAM", f"❌ Failed to start: {e}", Colors.FAIL)
    
    def open_browser(self):
        """Open the RAG Manager in the default browser"""
        try:
            url = f"http://localhost:{STREAMLIT_PORT}"
            webbrowser.open(url)
            self.log_message("BROWSER", f"🌐 Opened RAG Manager: {url}", Colors.OKGREEN)
        except Exception as e:
            self.log_message("BROWSER", f"❌ Could not open browser: {e}", Colors.WARNING)
            self.log_message("BROWSER", f"Please manually open: http://localhost:{STREAMLIT_PORT}", Colors.WARNING)
    
    def start_all(self):
        """Start both services"""
        if not self.check_dependencies():
            return False
        
        self.running = True
        
        # Start Streamlit first
        self.start_streamlit()
        
        # Wait a bit for Streamlit to initialize
        time.sleep(5)
        
        # Start Telegram bot
        self.start_telegram_bot()
        
        return True
    
    def stop_all(self):
        """Stop both services"""
        self.running = False
        
        self.log_message("LAUNCHER", "🛑 Shutting down services...", Colors.WARNING)
        
        if self.streamlit_process:
            try:
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=5)
                self.log_message("STREAMLIT", "✅ Stopped", Colors.WARNING)
            except subprocess.TimeoutExpired:
                self.streamlit_process.kill()
                self.log_message("STREAMLIT", "🔪 Force killed", Colors.WARNING)
            except Exception as e:
                self.log_message("STREAMLIT", f"❌ Error stopping: {e}", Colors.FAIL)
        
        if self.telegram_process:
            try:
                self.telegram_process.terminate()
                self.telegram_process.wait(timeout=5)
                self.log_message("TELEGRAM", "✅ Stopped", Colors.WARNING)
            except subprocess.TimeoutExpired:
                self.telegram_process.kill()
                self.log_message("TELEGRAM", "🔪 Force killed", Colors.WARNING)
            except Exception as e:
                self.log_message("TELEGRAM", f"❌ Error stopping: {e}", Colors.FAIL)
        
        self.log_message("LAUNCHER", "👋 All services stopped", Colors.OKGREEN)
    
    def wait_for_exit(self):
        """Wait for user to exit"""
        try:
            self.log_message("LAUNCHER", "✅ Both services are running!", Colors.OKGREEN)
            self.log_message("LAUNCHER", f"🌐 RAG Manager: http://localhost:{STREAMLIT_PORT}", Colors.OKCYAN)
            self.log_message("LAUNCHER", "📱 Check your Telegram bot status above", Colors.OKCYAN)
            self.log_message("LAUNCHER", "🛑 Press Ctrl+C to stop all services", Colors.WARNING)
            
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
                
                # Check if processes are still alive
                if self.streamlit_process and self.streamlit_process.poll() is not None:
                    self.log_message("STREAMLIT", "❌ Process died unexpectedly", Colors.FAIL)
                    self.running = False
                
                if self.telegram_process and self.telegram_process.poll() is not None:
                    self.log_message("TELEGRAM", "❌ Process died unexpectedly", Colors.FAIL)
                    self.running = False
                    
        except KeyboardInterrupt:
            self.log_message("LAUNCHER", "🛑 Received stop signal", Colors.WARNING)
        finally:
            self.stop_all()

def main():
    """Main launcher function"""
    manager = ProcessManager()
    
    # Print banner
    manager.print_banner()
    
    # Setup signal handlers for clean shutdown
    def signal_handler(signum, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(manager.stop_all)
    
    try:
        # Start all services
        if manager.start_all():
            # Wait for user to exit
            manager.wait_for_exit()
        else:
            print(f"{Colors.FAIL}❌ Failed to start services. Please check the errors above.{Colors.ENDC}")
            sys.exit(1)
            
    except Exception as e:
        print(f"{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")
        manager.stop_all()
        sys.exit(1)

if __name__ == "__main__":
    main() 