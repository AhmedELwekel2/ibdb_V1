#!/usr/bin/env python3
"""
Script to install Playwright browsers
"""

import sys
import subprocess

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("🔧 Installing Playwright browsers...")
    
    try:
        # Try to install using the playwright CLI
        result = subprocess.run([
            sys.executable, '-m', 'playwright', 'install', 'chromium'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Playwright browsers installed successfully!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Installation failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Installation timed out (took more than 10 minutes)")
        return False
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False

if __name__ == "__main__":
    success = install_playwright_browsers()
    if success:
        print("🎉 You can now run the bot with working Playwright scrapers!")
    else:
        print("💡 Alternative: Try running 'python -m playwright install chromium' manually")