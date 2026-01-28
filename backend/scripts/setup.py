# scripts/setup.py
"""Setup script to initialize the application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import get_settings


def create_directories():
    """Create necessary directories."""
    settings = get_settings()

    directories = [
        settings.STORAGE_DIR,
        settings.UPLOADS_DIR,
        settings.OUTPUTS_DIR,
        settings.PROMPTS_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env file not found!")
        print("Creating template .env file...")

        template = """# API Keys
OPENROUTER_API_KEY=your_key_here
OPENROUTER_DEFAULT_MODEL=anthropic/claude-3.5-sonnet

# Processing
MAX_CONCURRENCY=4
MAX_FILE_SIZE_MB=50

# Debug
DEBUG=True
"""
        env_path.write_text(template)
        print("✓ Created .env template. Please fill in your API keys.")
        return False

    print("✓ .env file configured")
    return True


def main():
    print("=" * 50)
    print("Menu Extractor API - Setup")
    print("=" * 50)

    env_ok = check_env_file()
    create_directories()

    print("\n" + "=" * 50)
    if env_ok:
        print("✓ Setup complete! Ready to run.")
        print("Start server: uvicorn backend.app:app --reload")
    else:
        print("⚠️  Setup incomplete. Please configure .env file.")
    print("=" * 50)


if __name__ == "__main__":
    main()
