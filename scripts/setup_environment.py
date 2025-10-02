"""Setup script for the Fantasy Football Valuation Engine environment."""

import subprocess
import sys
from pathlib import Path


def install_requirements():
    """Install required packages."""
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("requirements.txt not found!")
        return False
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False


def test_imports():
    """Test that key packages can be imported."""
    packages = [
        'pandas',
        'numpy', 
        'nflreadpy',
        'click',
        'pydantic'
    ]
    
    failed = []
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            failed.append(package)
    
    return len(failed) == 0


def create_directories():
    """Create necessary directories."""
    base_dir = Path(__file__).parent.parent
    directories = [
        "data/cache",
        "data/raw", 
        "data/processed",
        "logs",
        "output"
    ]
    
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def main():
    """Main setup function."""
    print("Setting up Fantasy Football Valuation Engine...")
    print("=" * 50)
    
    # Install requirements
    print("Installing requirements...")
    if not install_requirements():
        return
    
    # Test imports
    print("\nTesting package imports...")
    if not test_imports():
        print("Some packages failed to import. Please check the installation.")
        return
    
    # Create directories
    print("\nCreating directories...")
    create_directories()
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run the test: python main.py test")
    print("2. Generate projections: python main.py weekly --week 1")
    print("3. Explore data: jupyter notebook notebooks/data_exploration.ipynb")


if __name__ == "__main__":
    main()

