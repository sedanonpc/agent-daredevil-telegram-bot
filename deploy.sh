#!/bin/bash
# ===========================================
# Agent Daredevil - Deployment Script
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check environment
check_environment() {
    print_status "Checking environment..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Please copy env.example to .env and configure it."
        exit 1
    fi
    
    # Check required environment variables
    source .env
    
    required_vars=("TELEGRAM_API_ID" "TELEGRAM_API_HASH" "TELEGRAM_PHONE_NUMBER" "OPENAI_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    print_success "Environment check passed"
}

# Function to deploy with current Railway setup
deploy_railway_native() {
    print_status "Deploying with Railway native setup..."
    
    # Ensure we're using the native railway.json
    if [ -f "railway.docker.json" ]; then
        cp railway.json railway.docker.backup.json 2>/dev/null || true
    fi
    
    if [ -f "railway.native.json" ]; then
        cp railway.native.json railway.json
    else
        # Create native railway.json
        cat > railway.json << EOF
{
  "\$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "RAILPACK"
  },
  "deploy": {
    "startCommand": "python telegram_bot_rag.py",
    "runtime": "V2",
    "numReplicas": 1,
    "sleepApplication": false,
    "useLegacyStacker": false,
    "multiRegionConfig": {
      "us-east4-eqdc4a": {
        "numReplicas": 1
      }
    },
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF
    fi
    
    print_success "Railway native configuration ready"
    print_status "Push to your Railway-connected repository to deploy"
}

# Function to deploy with Docker
deploy_railway_docker() {
    print_status "Deploying with Docker on Railway..."
    
    # Check if Dockerfile exists
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile not found. Please ensure Dockerfile exists."
        exit 1
    fi
    
    # Use Docker railway configuration
    cp railway.docker.json railway.json
    
    print_success "Docker configuration ready"
    print_status "Push to your Railway-connected repository to deploy"
}

# Function to deploy locally with Docker
deploy_local_docker() {
    print_status "Deploying locally with Docker Compose..."
    
    # Check if Docker is installed
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if docker-compose.yml exists
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found."
        exit 1
    fi
    
    # Create data directories
    mkdir -p data logs temp_voice_files
    
    # Build and start services
    print_status "Building Docker images..."
    docker-compose build
    
    print_status "Starting services..."
    docker-compose up -d
    
    print_success "Services started successfully!"
    print_status "View logs with: docker-compose logs -f telegram-bot"
    print_status "Stop services with: docker-compose down"
}

# Function to deploy with web interfaces
deploy_local_with_web() {
    print_status "Deploying locally with web interfaces..."
    
    # Start with web interfaces profile
    docker-compose --profile web-interfaces up -d
    
    print_success "All services started successfully!"
    print_status "Telegram Bot: Running"
    print_status "RAG Manager: http://localhost:8501"
    print_status "Knowledge Visualizer: http://localhost:8502"
    print_status "Web Messenger: http://localhost:8080"
}

# Function to show help
show_help() {
    echo "Agent Daredevil Deployment Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  railway-native    Deploy with Railway's native Python setup"
    echo "  railway-docker    Deploy with Docker on Railway"
    echo "  local-docker      Deploy locally with Docker Compose"
    echo "  local-web         Deploy locally with web interfaces"
    echo "  check             Check environment configuration"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check              # Check environment"
    echo "  $0 railway-native     # Deploy to Railway (native)"
    echo "  $0 railway-docker     # Deploy to Railway (Docker)"
    echo "  $0 local-docker       # Deploy locally (bot only)"
    echo "  $0 local-web          # Deploy locally (with web UIs)"
}

# Main script logic
main() {
    case "${1:-help}" in
        "check")
            check_environment
            ;;
        "railway-native")
            check_environment
            deploy_railway_native
            ;;
        "railway-docker")
            check_environment
            deploy_railway_docker
            ;;
        "local-docker")
            check_environment
            deploy_local_docker
            ;;
        "local-web")
            check_environment
            deploy_local_with_web
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
