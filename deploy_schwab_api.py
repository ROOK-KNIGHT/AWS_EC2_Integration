#!/usr/bin/env python3
"""
Charles Schwab API Integration - Complete Deployment Script
This Python script creates a complete ecosystem and deploys the Schwab API integration
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class SchwabAPIDeployer:
    def __init__(self):
        self.system = platform.system().lower()
        self.home_dir = Path.home()
        self.desktop_dir = self.home_dir / "Desktop"
        self.project_name = "SchwabAPI"
        self.project_dir = self.desktop_dir / self.project_name
        self.repo_url = "https://github.com/ROOK-KNIGHT/AWS_EC2_Integration.git"
        self.repo_dir = self.project_dir / "AWS_EC2_Integration"
        
    def print_status(self, message, status="INFO"):
        colors = {
            "INFO": "\033[0;34m",
            "SUCCESS": "\033[0;32m", 
            "WARNING": "\033[1;33m",
            "ERROR": "\033[0;31m"
        }
        reset = "\033[0m"
        print(f"{colors.get(status, colors['INFO'])}[{status}]{reset} {message}")
        
    def print_header(self, title):
        print(f"\n{'='*50}")
        print(f"{title}")
        print(f"{'='*50}\n")
        
    def run_command(self, command, cwd=None, check=True):
        """Run a command and return the result"""
        try:
            self.print_status(f"Running: {command}")
            if isinstance(command, str):
                result = subprocess.run(command, shell=True, cwd=cwd, 
                                      capture_output=True, text=True, check=check)
            else:
                result = subprocess.run(command, cwd=cwd, 
                                      capture_output=True, text=True, check=check)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr and result.returncode != 0:
                print(result.stderr)
                
            return result
        except subprocess.CalledProcessError as e:
            self.print_status(f"Command failed: {e}", "ERROR")
            if not check:
                return e
            raise
            
    def create_directory_structure(self):
        """Create the project directory structure"""
        self.print_header("Creating Directory Structure")
        
        # Remove existing directory if it exists
        if self.project_dir.exists():
            self.print_status(f"Removing existing directory: {self.project_dir}", "WARNING")
            shutil.rmtree(self.project_dir)
            
        # Create new project directory
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.print_status(f"Created project directory: {self.project_dir}", "SUCCESS")
        
        # Change to project directory
        os.chdir(self.project_dir)
        self.print_status(f"Changed to directory: {os.getcwd()}", "SUCCESS")
        
    def install_system_dependencies(self):
        """Install system dependencies based on the operating system"""
        self.print_header("Installing System Dependencies")
        
        if self.system == "darwin":  # macOS
            self.print_status("Detected macOS - Installing via Homebrew")
            
            # Check if Homebrew is installed
            try:
                self.run_command("brew --version")
            except subprocess.CalledProcessError:
                self.print_status("Installing Homebrew...")
                self.run_command('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
                
            # Install dependencies
            self.run_command("brew install python3 git")
            
        elif self.system == "linux":
            self.print_status("Detected Linux - Installing via package manager")
            
            # Try different package managers
            try:
                self.run_command("sudo yum update -y && sudo yum install -y python3 python3-pip git")
            except subprocess.CalledProcessError:
                try:
                    self.run_command("sudo apt update && sudo apt install -y python3 python3-pip git")
                except subprocess.CalledProcessError:
                    self.print_status("Could not install dependencies automatically", "ERROR")
                    self.print_status("Please install Python 3 and Git manually", "ERROR")
                    return False
                    
        else:
            self.print_status(f"Unsupported operating system: {self.system}", "ERROR")
            return False
            
        self.print_status("System dependencies installed", "SUCCESS")
        return True
        
    def verify_installations(self):
        """Verify that required tools are installed"""
        self.print_header("Verifying Installations")
        
        # Check Python
        try:
            result = self.run_command("python3 --version")
            self.print_status(f"Python installed: {result.stdout.strip()}", "SUCCESS")
        except subprocess.CalledProcessError:
            self.print_status("Python 3 not found", "ERROR")
            return False
            
        # Check Git
        try:
            result = self.run_command("git --version")
            self.print_status(f"Git installed: {result.stdout.strip()}", "SUCCESS")
        except subprocess.CalledProcessError:
            self.print_status("Git not found", "ERROR")
            return False
            
        return True
        
    def clone_repository(self):
        """Clone the GitHub repository"""
        self.print_header("Cloning Repository")
        
        try:
            self.run_command(f"git clone {self.repo_url}")
            if self.repo_dir.exists():
                self.print_status("Repository cloned successfully", "SUCCESS")
                os.chdir(self.repo_dir)
                self.print_status(f"Changed to repository directory: {os.getcwd()}", "SUCCESS")
                return True
            else:
                self.print_status("Repository directory not found after cloning", "ERROR")
                return False
        except subprocess.CalledProcessError:
            self.print_status("Failed to clone repository", "ERROR")
            return False
            
    def setup_python_environment(self):
        """Set up Python virtual environment and install dependencies"""
        self.print_header("Setting up Python Environment")
        
        # Create virtual environment
        try:
            self.run_command("python3 -m venv schwab_env")
            self.print_status("Virtual environment created", "SUCCESS")
        except subprocess.CalledProcessError:
            self.print_status("Failed to create virtual environment", "ERROR")
            return False
            
        # Determine activation script path
        if self.system == "windows":
            activate_script = "schwab_env\\Scripts\\activate"
            python_cmd = "schwab_env\\Scripts\\python"
            pip_cmd = "schwab_env\\Scripts\\pip"
        else:
            activate_script = "schwab_env/bin/activate"
            python_cmd = "schwab_env/bin/python"
            pip_cmd = "schwab_env/bin/pip"
            
        # Install dependencies
        try:
            self.run_command(f"{pip_cmd} install --upgrade pip")
            self.run_command(f"{pip_cmd} install -r requirements.txt")
            self.print_status("Python dependencies installed", "SUCCESS")
        except subprocess.CalledProcessError:
            self.print_status("Failed to install Python dependencies", "ERROR")
            return False
            
        return True
        
    def collect_credentials(self):
        """Collect all required credentials from user"""
        self.print_header("Collecting Required Credentials")
        
        credentials = {}
        
        print("Please provide the following credentials for your Charles Schwab API integration:")
        print("(You can find these in your Charles Schwab Developer Portal)")
        print()
        
        # Schwab API Credentials
        self.print_status("Charles Schwab API Credentials:", "INFO")
        credentials['SCHWAB_APP_KEY'] = input("Enter your Schwab App Key: ").strip()
        credentials['SCHWAB_APP_SECRET'] = input("Enter your Schwab App Secret: ").strip()
        
        # Callback URI
        print("\nCallback URI Options:")
        print("1. Local development (https://127.0.0.1:8080/callback)")
        print("2. Custom callback URI")
        callback_choice = input("Choose callback URI (1 or 2): ").strip()
        
        if callback_choice == "2":
            credentials['SCHWAB_REDIRECT_URI'] = input("Enter your custom callback URI: ").strip()
        else:
            credentials['SCHWAB_REDIRECT_URI'] = "https://127.0.0.1:8080/callback"
        
        # AWS Credentials (optional)
        print("\nAWS Configuration (optional - for cloud deployment):")
        aws_choice = input("Do you want to configure AWS credentials? (y/n): ").lower().strip()
        
        if aws_choice in ['y', 'yes']:
            credentials['AWS_REGION'] = input("Enter AWS Region (default: us-east-1): ").strip() or "us-east-1"
            credentials['AWS_ACCESS_KEY_ID'] = input("Enter AWS Access Key ID: ").strip()
            credentials['AWS_SECRET_ACCESS_KEY'] = input("Enter AWS Secret Access Key: ").strip()
        else:
            credentials['AWS_REGION'] = "us-east-1"
            credentials['AWS_ACCESS_KEY_ID'] = "your_access_key_here"
            credentials['AWS_SECRET_ACCESS_KEY'] = "your_secret_key_here"
        
        # Application Configuration
        port = input("Enter application port (default: 8080): ").strip()
        credentials['PORT'] = port if port else "8080"
        
        log_level = input("Enter log level (INFO/DEBUG/WARNING/ERROR, default: INFO): ").strip().upper()
        credentials['LOG_LEVEL'] = log_level if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'] else "INFO"
        
        # Generate a random secret key
        import secrets
        credentials['SECRET_KEY'] = secrets.token_urlsafe(32)
        
        credentials['APP_ENV'] = "development"
        credentials['SCHWAB_TOKEN_FILE'] = "cs_tokens.json"
        
        return credentials
        
    def setup_configuration(self):
        """Set up configuration files with collected credentials"""
        self.print_header("Setting up Configuration")
        
        # Collect credentials from user
        credentials = self.collect_credentials()
        
        # Validate required credentials
        required_fields = ['SCHWAB_APP_KEY', 'SCHWAB_APP_SECRET']
        for field in required_fields:
            if not credentials.get(field) or credentials[field] == f"your_{field.lower()}_here":
                self.print_status(f"Missing required credential: {field}", "ERROR")
                return False
        
        # Create .env file with collected credentials
        env_content = f"""# Charles Schwab API Configuration
SCHWAB_APP_KEY={credentials['SCHWAB_APP_KEY']}
SCHWAB_APP_SECRET={credentials['SCHWAB_APP_SECRET']}
SCHWAB_REDIRECT_URI={credentials['SCHWAB_REDIRECT_URI']}

# AWS Configuration
AWS_REGION={credentials['AWS_REGION']}
AWS_ACCESS_KEY_ID={credentials['AWS_ACCESS_KEY_ID']}
AWS_SECRET_ACCESS_KEY={credentials['AWS_SECRET_ACCESS_KEY']}

# Application Configuration
PORT={credentials['PORT']}
LOG_LEVEL={credentials['LOG_LEVEL']}
APP_ENV={credentials['APP_ENV']}
SECRET_KEY={credentials['SECRET_KEY']}

# Token Storage
SCHWAB_TOKEN_FILE={credentials['SCHWAB_TOKEN_FILE']}
"""
        
        env_file = Path(".env")
        with open(env_file, 'w') as f:
            f.write(env_content)
            
        self.print_status(".env file created with your credentials", "SUCCESS")
        
        # Show summary of configuration
        print("\n" + "="*50)
        print("Configuration Summary:")
        print("="*50)
        print(f"Schwab App Key: {credentials['SCHWAB_APP_KEY'][:8]}...")
        print(f"Callback URI: {credentials['SCHWAB_REDIRECT_URI']}")
        print(f"AWS Region: {credentials['AWS_REGION']}")
        print(f"Application Port: {credentials['PORT']}")
        print(f"Log Level: {credentials['LOG_LEVEL']}")
        if credentials['AWS_ACCESS_KEY_ID'] != "your_access_key_here":
            print(f"AWS Access Key: {credentials['AWS_ACCESS_KEY_ID'][:8]}...")
        print("="*50)
        
        return True
        
    def create_startup_scripts(self):
        """Create startup and helper scripts"""
        self.print_header("Creating Startup Scripts")
        
        # Create run script
        if self.system == "windows":
            run_script = "run_schwab_api.bat"
            script_content = f"""@echo off
cd /d "{self.repo_dir}"
echo Starting Charles Schwab API Integration...
echo Project Directory: %CD%

schwab_env\\Scripts\\activate
if not exist .env (
    echo ERROR: .env file not found!
    echo Please edit .env file and add your Schwab API credentials
    pause
    exit /b 1
)

echo Starting Flask application...
schwab_env\\Scripts\\python app.py
pause
"""
        else:
            run_script = "run_schwab_api.sh"
            script_content = f"""#!/bin/bash
cd "{self.repo_dir}"
echo "Starting Charles Schwab API Integration..."
echo "Project Directory: $(pwd)"

source schwab_env/bin/activate

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please edit .env file and add your Schwab API credentials"
    exit 1
fi

echo "Starting Flask application..."
python app.py
"""
            
        with open(run_script, 'w') as f:
            f.write(script_content)
            
        if self.system != "windows":
            os.chmod(run_script, 0o755)
            
        self.print_status(f"Startup script created: {run_script}", "SUCCESS")
        
        # Create desktop shortcut
        self.create_desktop_shortcut(run_script)
        
        return True
        
    def create_desktop_shortcut(self, run_script):
        """Create desktop shortcut"""
        if self.system == "darwin":  # macOS
            shortcut_path = self.desktop_dir / "Schwab API.command"
            shortcut_content = f"""#!/bin/bash
cd "{self.repo_dir}"
./{run_script}
"""
            with open(shortcut_path, 'w') as f:
                f.write(shortcut_content)
            os.chmod(shortcut_path, 0o755)
            self.print_status("Desktop shortcut created (macOS)", "SUCCESS")
            
        elif self.system == "windows":
            # Create Windows shortcut (simplified)
            shortcut_path = self.desktop_dir / "Schwab API.bat"
            shortcut_content = f"""@echo off
cd /d "{self.repo_dir}"
{run_script}
"""
            with open(shortcut_path, 'w') as f:
                f.write(shortcut_content)
            self.print_status("Desktop shortcut created (Windows)", "SUCCESS")
            
    def deploy_to_aws(self):
        """Deploy to AWS if requested"""
        self.print_header("AWS Deployment Option")
        
        response = input("Do you want to deploy to AWS EC2? (y/n): ").lower().strip()
        
        if response == 'y' or response == 'yes':
            self.print_status("Starting AWS deployment...")
            
            # Check if AWS CLI is configured
            try:
                self.run_command("aws sts get-caller-identity")
                self.print_status("AWS CLI is configured", "SUCCESS")
            except subprocess.CalledProcessError:
                self.print_status("AWS CLI not configured. Please run 'aws configure' first", "ERROR")
                return False
                
            # Run AWS deployment script
            try:
                aws_script = Path("aws/deploy.sh")
                if aws_script.exists():
                    self.run_command("./aws/deploy.sh")
                    self.print_status("AWS deployment completed", "SUCCESS")
                else:
                    self.print_status("AWS deployment script not found", "ERROR")
                    return False
            except subprocess.CalledProcessError:
                self.print_status("AWS deployment failed", "ERROR")
                return False
        else:
            self.print_status("Skipping AWS deployment", "INFO")
            
        return True
        
    def show_completion_message(self):
        """Show completion message with next steps"""
        self.print_header("Setup Complete!")
        
        print("🎉 Charles Schwab API Integration has been set up successfully!")
        print()
        print(f"📁 Project Location: {self.repo_dir}")
        print()
        print("📋 Next Steps:")
        print("1. ✅ Credentials configured - Your API keys are already set up!")
        print()
        print("2. Run the application:")
        if self.system == "windows":
            print("   - Double-click 'run_schwab_api.bat'")
            print("   - Or double-click the desktop shortcut 'Schwab API.bat'")
        else:
            print("   - Run: ./run_schwab_api.sh")
            print("   - Or double-click the desktop shortcut 'Schwab API.command'")
        print()
        print("3. Open your browser to: http://localhost:8080")
        print()
        print("4. Authenticate with Charles Schwab using one of these methods:")
        print("   - OAuth flow (recommended)")
        print("   - Manual callback URL processing")
        print("   - Direct token entry")
        print()
        print("📚 Files created:")
        print("- .env (configuration file with your credentials)")
        print("- schwab_env/ (Python virtual environment)")
        print("- run_schwab_api.sh/.bat (startup script)")
        print("- Desktop shortcut for easy access")
        print()
        print("🚀 Ready to trade! Your Charles Schwab API integration is fully configured.")
        print()
        
    def deploy(self):
        """Main deployment function"""
        try:
            self.print_header("Charles Schwab API Integration - Complete Deployment")
            
            # Step 1: Create directory structure
            self.create_directory_structure()
            
            # Step 2: Install system dependencies
            if not self.install_system_dependencies():
                return False
                
            # Step 3: Verify installations
            if not self.verify_installations():
                return False
                
            # Step 4: Clone repository
            if not self.clone_repository():
                return False
                
            # Step 5: Setup Python environment
            if not self.setup_python_environment():
                return False
                
            # Step 6: Setup configuration
            if not self.setup_configuration():
                return False
                
            # Step 7: Create startup scripts
            if not self.create_startup_scripts():
                return False
                
            # Step 8: Optional AWS deployment
            self.deploy_to_aws()
            
            # Step 9: Show completion message
            self.show_completion_message()
            
            return True
            
        except KeyboardInterrupt:
            self.print_status("Deployment interrupted by user", "WARNING")
            return False
        except Exception as e:
            self.print_status(f"Unexpected error: {e}", "ERROR")
            return False

def main():
    """Main function"""
    deployer = SchwabAPIDeployer()
    success = deployer.deploy()
    
    if success:
        print("\n✅ Deployment completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
