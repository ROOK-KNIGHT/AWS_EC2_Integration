#!/bin/bash

# Charles Schwab API Integration - Complete Setup Script
# This script creates a complete ecosystem for the Schwab API integration

set -e  # Exit on any error

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

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Main setup function
main() {
    print_header "Charles Schwab API Integration - Complete Setup"
    
    # Step 1: Create directory structure
    print_status "Creating directory structure on Desktop..."
    
    # Determine the Desktop path based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        DESKTOP_PATH="$HOME/Desktop"
        PACKAGE_MANAGER="brew"
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        DESKTOP_PATH="$HOME/Desktop"
        if command -v yum &> /dev/null; then
            PACKAGE_MANAGER="yum"
        elif command -v apt &> /dev/null; then
            PACKAGE_MANAGER="apt"
        else
            PACKAGE_MANAGER="unknown"
        fi
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Create project directory
    PROJECT_DIR="$DESKTOP_PATH/SchwabAPI"
    print_status "Creating project directory: $PROJECT_DIR"
    
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Directory $PROJECT_DIR already exists. Removing old version..."
        rm -rf "$PROJECT_DIR"
    fi
    
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    print_success "Created project directory: $PROJECT_DIR"
    
    # Step 2: Install system dependencies
    print_header "Installing System Dependencies"
    
    case $PACKAGE_MANAGER in
        "brew")
            print_status "Installing dependencies via Homebrew..."
            if ! command -v brew &> /dev/null; then
                print_status "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python3 git
            ;;
        "yum")
            print_status "Installing dependencies via yum..."
            sudo yum update -y
            sudo yum install -y python3 python3-pip git
            ;;
        "apt")
            print_status "Installing dependencies via apt..."
            sudo apt update
            sudo apt install -y python3 python3-pip git
            ;;
        *)
            print_error "Unknown package manager. Please install Python 3 and Git manually."
            exit 1
            ;;
    esac
    
    print_success "System dependencies installed"
    
    # Step 3: Verify installations
    print_header "Verifying Installations"
    
    if command -v $PYTHON_CMD &> /dev/null; then
        PYTHON_VERSION=$($PYTHON_CMD --version)
        print_success "Python installed: $PYTHON_VERSION"
    else
        print_error "Python 3 installation failed"
        exit 1
    fi
    
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version)
        print_success "Git installed: $GIT_VERSION"
    else
        print_error "Git installation failed"
        exit 1
    fi
    
    # Step 4: Clone the repository
    print_header "Cloning Charles Schwab API Repository"
    
    print_status "Cloning repository from GitHub..."
    git clone https://github.com/ROOK-KNIGHT/AWS_EC2_Integration.git
    
    if [ -d "AWS_EC2_Integration" ]; then
        print_success "Repository cloned successfully"
        cd AWS_EC2_Integration
    else
        print_error "Failed to clone repository"
        exit 1
    fi
    
    # Step 5: Set up Python virtual environment
    print_header "Setting up Python Virtual Environment"
    
    print_status "Creating virtual environment..."
    $PYTHON_CMD -m venv schwab_env
    
    print_status "Activating virtual environment..."
    source schwab_env/bin/activate
    
    print_success "Virtual environment created and activated"
    
    # Step 6: Install Python dependencies
    print_header "Installing Python Dependencies"
    
    print_status "Upgrading pip..."
    python -m pip install --upgrade pip
    
    print_status "Installing required packages..."
    pip install -r requirements.txt
    
    print_success "Python dependencies installed"
    
    # Step 7: Set up configuration
    print_header "Setting up Configuration"
    
    print_status "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
    else
        print_warning ".env.example not found, creating basic .env file"
        cat > .env << EOF
# Charles Schwab API Configuration
SCHWAB_APP_KEY=your_app_key_here
SCHWAB_APP_SECRET=your_app_secret_here
SCHWAB_REDIRECT_URI=https://127.0.0.1:8080/callback

# AWS Configuration (optional for local development)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Application Configuration
PORT=8080
LOG_LEVEL=INFO
APP_ENV=development
SECRET_KEY=dev-secret-key-change-in-production

# Token Storage
SCHWAB_TOKEN_FILE=cs_tokens.json
EOF
    fi
    
    # Step 8: Create startup script
    print_header "Creating Startup Scripts"
    
    # Create run script
    cat > run_schwab_api.sh << 'EOF'
#!/bin/bash

# Charles Schwab API - Startup Script
cd "$(dirname "$0")"

echo "Starting Charles Schwab API Integration..."
echo "Project Directory: $(pwd)"

# Activate virtual environment
source schwab_env/bin/activate

# Check if .env file exists and has credentials
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and add your Schwab API credentials"
    exit 1
fi

# Start the application
echo "Starting Flask application..."
python app.py
EOF
    
    chmod +x run_schwab_api.sh
    
    # Create setup completion script
    cat > complete_setup.sh << 'EOF'
#!/bin/bash

echo "=== Charles Schwab API Integration Setup ==="
echo ""
echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your Schwab API credentials:"
echo "   - SCHWAB_APP_KEY=your_actual_app_key"
echo "   - SCHWAB_APP_SECRET=your_actual_app_secret"
echo ""
echo "2. Run the application:"
echo "   ./run_schwab_api.sh"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:8080"
echo ""
echo "Project location: $(pwd)"
echo ""
echo "Files created:"
echo "- run_schwab_api.sh (startup script)"
echo "- .env (configuration file - EDIT THIS!)"
echo "- schwab_env/ (Python virtual environment)"
echo ""
EOF
    
    chmod +x complete_setup.sh
    
    print_success "Startup scripts created"
    
    # Step 9: Final setup completion
    print_header "Setup Complete!"
    
    print_success "Charles Schwab API Integration has been set up successfully!"
    echo ""
    print_status "Project Location: $PROJECT_DIR/AWS_EC2_Integration"
    echo ""
    print_status "Next Steps:"
    echo "1. Edit the .env file with your Schwab API credentials"
    echo "2. Run: ./run_schwab_api.sh"
    echo "3. Open browser to: http://localhost:8080"
    echo ""
    
    # Create desktop shortcut (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_status "Creating desktop shortcut..."
        cat > "$DESKTOP_PATH/Schwab API.command" << EOF
#!/bin/bash
cd "$PROJECT_DIR/AWS_EC2_Integration"
./run_schwab_api.sh
EOF
        chmod +x "$DESKTOP_PATH/Schwab API.command"
        print_success "Desktop shortcut created: Schwab API.command"
    fi
    
    # Run completion script
    ./complete_setup.sh
}

# Run main function
main "$@"
