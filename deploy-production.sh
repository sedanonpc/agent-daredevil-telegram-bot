#!/bin/bash
# ===========================================
# Agent Daredevil - Production Deployment Script
# ===========================================
# Automated deployment script for Railway production environment

set -e  # Exit on any error

echo "🎯 Agent Daredevil - Production Deployment"
echo "=========================================="

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

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI is not installed. Please install it first:"
        echo "npm install -g @railway/cli"
        exit 1
    fi
    
    print_success "All dependencies are installed"
}

# Check if .env file exists and has required variables
check_environment() {
    print_status "Checking environment configuration..."
    
    if [ ! -f .env ]; then
        print_error ".env file not found. Please create one based on env.example"
        exit 1
    fi
    
    # Check for required environment variables
    required_vars=(
        "TELEGRAM_API_ID"
        "TELEGRAM_API_HASH"
        "TELEGRAM_PHONE_NUMBER"
        "OPENAI_API_KEY"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    print_success "Environment configuration is valid"
}

# Build Docker image locally for testing
build_docker_image() {
    print_status "Building Docker image locally..."
    
    docker build -t agent-daredevil:latest .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Test Docker container locally
test_docker_container() {
    print_status "Testing Docker container locally..."
    
    # Start container in background
    docker run -d --name agent-daredevil-test \
        --env-file .env \
        -p 8000:8000 \
        agent-daredevil:latest
    
    # Wait for container to start
    sleep 10
    
    # Test health endpoint
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Container health check passed"
    else
        print_error "Container health check failed"
        docker logs agent-daredevil-test
        docker stop agent-daredevil-test
        docker rm agent-daredevil-test
        exit 1
    fi
    
    # Clean up test container
    docker stop agent-daredevil-test
    docker rm agent-daredevil-test
    
    print_success "Local Docker test completed successfully"
}

# Deploy to Railway
deploy_to_railway() {
    print_status "Deploying to Railway..."
    
    # Check if user is logged in to Railway
    if ! railway whoami &> /dev/null; then
        print_error "Not logged in to Railway. Please run: railway login"
        exit 1
    fi
    
    # Deploy to Railway
    railway up --detach
    
    if [ $? -eq 0 ]; then
        print_success "Deployment to Railway completed successfully"
    else
        print_error "Failed to deploy to Railway"
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Get Railway service URL
    service_url=$(railway domain)
    
    if [ -z "$service_url" ]; then
        print_warning "Could not get service URL from Railway"
        return
    fi
    
    print_status "Service URL: https://$service_url"
    
    # Test health endpoint
    if curl -f "https://$service_url/health" > /dev/null 2>&1; then
        print_success "Production deployment health check passed"
        print_success "🎯 Agent Daredevil is now live at: https://$service_url"
    else
        print_warning "Health check failed, but deployment may still be starting up"
        print_status "Check Railway dashboard for deployment status"
    fi
}

# Main deployment flow
main() {
    echo "Starting production deployment process..."
    echo
    
    check_dependencies
    check_environment
    build_docker_image
    test_docker_container
    deploy_to_railway
    verify_deployment
    
    echo
    print_success "🎯 Production deployment completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Monitor the deployment in Railway dashboard"
    echo "2. Check logs: railway logs"
    echo "3. Test the web interface and Telegram bot"
    echo "4. Set up monitoring and alerts"
}

# Run main function
main "$@"
