#!/usr/bin/env python3
"""
Agent Daredevil - Comprehensive Service Launcher
===============================================

Launches all necessary services for the Telegram RAG bot:
- Telegram Bot (telegram_bot_rag.py) - Main bot with RAG, memory, and character features
- RAG Manager (rag_manager.py) - Knowledge base management web interface  
- Knowledge Visualizer (rag_knowledge_visualizer.py) - Interactive knowledge visualization

This launcher handles dependency checking, service management, and graceful shutdown.
"""

import os
import sys
import subprocess
import time
import signal
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Try to import psutil, install if missing
try:
    import psutil
except ImportError:
    print("📦 Installing psutil for process management...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

class ServiceManager:
    """Manages multiple services with process monitoring and graceful shutdown"""
    
    def __init__(self):
        self.services: Dict[str, Dict] = {}
        self.running = False
        self.shutdown_event = threading.Event()
        
    def add_service(self, name: str, command: List[str], port: Optional[int] = None, 
                   working_dir: str = ".", auto_open: bool = False, critical: bool = False):
        """Add a service to be managed"""
        self.services[name] = {
            'command': command,
            'port': port,
            'working_dir': working_dir,
            'auto_open': auto_open,
            'critical': critical,
            'process': None,
            'status': 'stopped',
            'start_time': None,
            'restart_count': 0
        }
    
    def start_service(self, name: str) -> bool:
        """Start a specific service"""
        if name not in self.services:
            print(f"❌ Service '{name}' not found")
            return False
            
        service = self.services[name]
        
        if service['status'] == 'running':
            print(f"⚠️ Service '{name}' is already running")
            return True
        
        try:
            print(f"🚀 Starting {name}...")
            
            # Start the process
            process = subprocess.Popen(
                service['command'],
                cwd=service['working_dir'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Update service info
            service['process'] = process
            service['status'] = 'starting'
            service['start_time'] = datetime.now()
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if still running
            if process.poll() is None:
                service['status'] = 'running'
                print(f"✅ {name} started successfully (PID: {process.pid})")
                
                # Auto-open browser for web services
                if service['auto_open'] and service['port']:
                    threading.Timer(3.0, self._open_browser, args=[service['port']]).start()
                
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ {name} failed to start")
                if stderr:
                    print(f"   Error: {stderr}")
                service['status'] = 'failed'
                return False
                
        except Exception as e:
            print(f"❌ Error starting {name}: {e}")
            service['status'] = 'failed'
            return False
    
    def stop_service(self, name: str) -> bool:
        """Stop a specific service"""
        if name not in self.services:
            return False
            
        service = self.services[name]
        
        if service['status'] != 'running' or not service['process']:
            return True
        
        try:
            print(f"🛑 Stopping {name}...")
            
            # Try graceful shutdown first
            service['process'].terminate()
            
            # Wait for graceful shutdown
            try:
                service['process'].wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   Force killing {name}...")
                service['process'].kill()
                service['process'].wait()
            
            service['status'] = 'stopped'
            service['process'] = None
            print(f"✅ {name} stopped")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping {name}: {e}")
            return False
    
    def start_all_services(self) -> bool:
        """Start all services in order"""
        print("🚀 Starting all services...")
        
        # Start critical services first
        critical_services = [name for name, service in self.services.items() if service['critical']]
        other_services = [name for name, service in self.services.items() if not service['critical']]
        
        success = True
        
        # Start critical services
        for name in critical_services:
            if not self.start_service(name):
                print(f"❌ Critical service '{name}' failed to start!")
                success = False
                if self.services[name]['critical']:
                    return False  # Don't continue if critical service fails
        
        # Wait a bit for critical services to stabilize
        if critical_services:
            time.sleep(3)
        
        # Start other services
        for name in other_services:
            if not self.start_service(name):
                success = False
            time.sleep(2)  # Small delay between service starts
        
        return success
    
    def stop_all_services(self):
        """Stop all services gracefully"""
        print("🛑 Stopping all services...")
        
        # Stop in reverse order
        service_names = list(self.services.keys())
        for name in reversed(service_names):
            self.stop_service(name)
    
    def monitor_services(self):
        """Monitor running services and restart if needed"""
        while self.running and not self.shutdown_event.is_set():
            for name, service in self.services.items():
                if service['status'] == 'running' and service['process']:
                    # Check if process is still alive
                    if service['process'].poll() is not None:
                        print(f"⚠️ Service '{name}' has stopped unexpectedly")
                        service['status'] = 'failed'
                        
                        # Auto-restart critical services
                        if service['critical'] and service['restart_count'] < 3:
                            print(f"🔄 Restarting {name} (attempt {service['restart_count'] + 1}/3)")
                            service['restart_count'] += 1
                            self.start_service(name)
            
            # Check every 10 seconds
            self.shutdown_event.wait(10)
    
    def _open_browser(self, port: int):
        """Open browser to service URL"""
        url = f"http://localhost:{port}"
        try:
            webbrowser.open(url)
            print(f"🌐 Opened {url} in browser")
        except Exception as e:
            print(f"⚠️ Could not open browser: {e}")
    
    def run(self):
        """Run the service manager"""
        self.running = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_services, daemon=True)
        monitor_thread.start()
        
        try:
            # Start all services
            if self.start_all_services():
                print("\n✅ All services started successfully!")
                self._print_status()
                
                # Keep running until interrupted
                print("\n🎯 Agent Daredevil is now running!")
                print("📱 Access the web interfaces:")
                print("   • RAG Manager: http://localhost:8501")
                print("   • Knowledge Visualizer: http://localhost:8502")
                print("\n⏹️ Press Ctrl+C to stop all services")
                
                # Wait for interrupt
                self.shutdown_event.wait()
            else:
                print("❌ Failed to start all services")
                
        except KeyboardInterrupt:
            print("\n👋 Shutdown requested by user")
        finally:
            self.running = False
            self.stop_all_services()
    
    def _print_status(self):
        """Print current status of all services"""
        print("\n📊 Service Status:")
        print("-" * 50)
        for name, service in self.services.items():
            status = service['status']
            emoji = "✅" if status == "running" else "❌" if status == "failed" else "⏸️"
            port_info = f" (:{service['port']})" if service['port'] else ""
            print(f"   {emoji} {name}{port_info} - {status}")

def check_dependencies() -> bool:
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'telethon', 'openai', 'streamlit', 'chromadb', 'langchain', 
        'langchain_openai', 'langchain_community', 'pandas', 'numpy',
        'python-dotenv', 'streamlit-echarts', 'pyecharts', 'networkx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            package_name = package.replace('-', '_')
            __import__(package_name)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing dependencies: {', '.join(missing_packages)}")
        
        response = input("\nWould you like to install missing dependencies? (y/n): ").lower()
        if response in ['y', 'yes']:
            try:
                print("📦 Installing dependencies...")
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
                print("✅ Dependencies installed successfully!")
                return True
            except Exception as e:
                print(f"❌ Error installing dependencies: {e}")
                return False
        else:
            print("\nTo install manually:")
            print("pip install " + " ".join(missing_packages))
            return False
    
    print("✅ All dependencies are installed")
    return True

def check_environment() -> bool:
    """Check if environment is properly configured"""
    print("🔍 Checking environment configuration...")
    
    required_files = [
        'telegram_bot_rag.py',
        'rag_manager.py', 
        'rag_knowledge_visualizer.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    # Check environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ python-dotenv not found, skipping .env file loading")
    
    required_env_vars = [
        'TELEGRAM_API_ID',
        'TELEGRAM_API_HASH', 
        'TELEGRAM_PHONE_NUMBER',
        'OPENAI_API_KEY'
    ]
    
    missing_env_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_env_vars.append(var)
    
    if missing_env_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_env_vars)}")
        print("Please configure these in your .env file")
        return False
    
    print("✅ Environment is properly configured")
    return True

def check_ports() -> bool:
    """Check if required ports are available"""
    print("🔍 Checking port availability...")
    
    required_ports = [8501, 8502]
    
    for port in required_ports:
        if is_port_in_use(port):
            print(f"❌ Port {port} is already in use")
            return False
    
    print("✅ All required ports are available")
    return True

def is_port_in_use(port: int) -> bool:
    """Check if a port is currently in use"""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    except:
        # Fallback method
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

def create_service_config() -> ServiceManager:
    """Create and configure the service manager"""
    manager = ServiceManager()
    
    # Add Telegram Bot (critical service)
    manager.add_service(
        name="Telegram Bot",
        command=[sys.executable, "telegram_bot_rag.py"],
        critical=True,
        auto_open=False
    )
    
    # Add RAG Manager Web Interface
    manager.add_service(
        name="RAG Manager",
        command=[sys.executable, "-m", "streamlit", "run", "rag_manager.py", 
                "--server.port", "8501", "--server.headless", "true", 
                "--browser.gatherUsageStats", "false"],
        port=8501,
        auto_open=True
    )
    
    # Add Knowledge Visualizer Web Interface  
    manager.add_service(
        name="Knowledge Visualizer",
        command=[sys.executable, "-m", "streamlit", "run", "rag_knowledge_visualizer.py",
                "--server.port", "8502", "--server.headless", "true",
                "--browser.gatherUsageStats", "false"],
        port=8502,
        auto_open=True
    )
    
    return manager

def main():
    """Main launcher function"""
    print("🎯 Agent Daredevil - Comprehensive Service Launcher")
    print("=" * 60)
    print("🤖 Telegram RAG Bot with Memory & Knowledge Management")
    print("=" * 60)
    
    # Pre-flight checks
    if not check_dependencies():
        print("\n❌ Dependency check failed")
        print("Please install missing dependencies and try again")
        sys.exit(1)
    
    if not check_environment():
        print("\n❌ Environment check failed") 
        print("Please configure your environment and try again")
        sys.exit(1)
    
    if not check_ports():
        print("\n❌ Port check failed")
        print("Please close applications using the required ports and try again")
        sys.exit(1)
    
    print("\n✅ All pre-flight checks passed!")
    
    # Create and run service manager
    manager = create_service_config()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}")
        manager.shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        manager.run()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        manager.stop_all_services()
        sys.exit(1)
    
    print("\n👋 Agent Daredevil services stopped")
    print("Thanks for using Agent Daredevil! 🎯")

if __name__ == "__main__":
    main() 