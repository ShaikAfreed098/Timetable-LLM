#!/usr/bin/env python3
"""
Timetable LLM - Health Check & Setup Validator
Validates environment, dependencies, and configuration before startup.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_status(status, message):
    """Print colored status messages"""
    if status == 'ok':
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
    elif status == 'warn':
        print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")
    elif status == 'error':
        print(f"{Colors.RED}✗{Colors.RESET} {message}")
    elif status == 'info':
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")

def check_python():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print_status('ok', f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    else:
        print_status('error', f"Python 3.11+ required (found {version.major}.{version.minor})")
        return False

def check_node():
    """Check Node.js version"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print_status('ok', f"Node.js {version} ✓")
        return True
    except FileNotFoundError:
        print_status('error', "Node.js not found. Install from https://nodejs.org")
        return False

def check_git():
    """Check Git installation"""
    try:
        subprocess.run(['git', '--version'], capture_output=True, text=True, check=True)
        print_status('ok', "Git installed ✓")
        return True
    except FileNotFoundError:
        print_status('warn', "Git not found (optional)")
        return True

def check_env_file():
    """Check .env file exists and has required vars"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print_status('error', ".env file not found")
        return False
    
    print_status('ok', ".env file exists ✓")
    
    # Check required variables
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    required = [
        'JWT_SECRET',
        'REDIS_URL',
        'DATABASE_URL',
        'ENVIRONMENT',
        'DEBUG'
    ]
    
    missing = [v for v in required if v not in env_vars]
    
    if missing:
        print_status('error', f"Missing required variables: {', '.join(missing)}")
        return False
    
    print_status('ok', f"All required variables set ✓")
    
    # Check JWT_SECRET length
    jwt_secret = env_vars.get('JWT_SECRET', '')
    if len(jwt_secret) < 32:
        print_status('warn', f"JWT_SECRET too short ({len(jwt_secret)} chars, recommended 32+)")
    else:
        print_status('ok', f"JWT_SECRET length valid ✓")
    
    return True

def check_directories():
    """Check required directories exist"""
    dirs = [
        Path('backend'),
        Path('frontend'),
        Path('backend/app'),
        Path('backend/alembic'),
        Path('frontend/src'),
    ]
    
    all_ok = True
    for d in dirs:
        if d.exists():
            print_status('ok', f"Directory {d} exists ✓")
        else:
            print_status('error', f"Missing directory: {d}")
            all_ok = False
    
    return all_ok

def check_requirements():
    """Check requirements.txt exists"""
    req_path = Path('backend/requirements.txt')
    if req_path.exists():
        print_status('ok', "backend/requirements.txt exists ✓")
        return True
    else:
        print_status('error', "backend/requirements.txt not found")
        return False

def check_package_json():
    """Check package.json exists"""
    pkg_path = Path('frontend/package.json')
    if pkg_path.exists():
        print_status('ok', "frontend/package.json exists ✓")
        return True
    else:
        print_status('error', "frontend/package.json not found")
        return False

def check_docker():
    """Check Docker installation (optional)"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print_status('ok', f"Docker installed ({version}) ✓")
        
        # Check docker-compose
        result = subprocess.run(['docker', 'compose', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print_status('ok', f"Docker Compose installed ({version}) ✓")
        return True
    except FileNotFoundError:
        print_status('warn', "Docker/Docker Compose not found (required for Option A)")
        return False

def validate_database_url():
    """Validate DATABASE_URL format"""
    env_path = Path('.env')
    with open(env_path) as f:
        for line in f:
            if line.startswith('DATABASE_URL'):
                _, value = line.split('=', 1)
                value = value.strip().strip('"\'')
                
                if 'postgresql' in value or 'postgres' in value:
                    print_status('ok', f"DATABASE_URL uses PostgreSQL ✓")
                    return True
                elif 'mysql' in value:
                    print_status('error', "DATABASE_URL uses MySQL (should be PostgreSQL)")
                    return False
                else:
                    print_status('warn', f"DATABASE_URL format unclear: {value[:50]}...")
                    return True
    
    return False

def main():
    """Run all checks"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("Timetable LLM - Pre-Startup Validation")
    print(f"{'='*60}{Colors.RESET}\n")
    
    checks = [
        ("Python 3.11+", check_python),
        ("Node.js 20+", check_node),
        ("Git", check_git),
        ("Project structure", check_directories),
        (".env configuration", check_env_file),
        ("Database URL", validate_database_url),
        ("Backend requirements", check_requirements),
        ("Frontend package.json", check_package_json),
        ("Docker (optional)", check_docker),
    ]
    
    results = {}
    print(f"{Colors.BLUE}Running checks...{Colors.RESET}\n")
    
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            results[name] = check_func()
        except Exception as e:
            print_status('error', f"Check failed: {e}")
            results[name] = False
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("Summary")
    print(f"{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = 'ok' if result else 'error'
        print_status(status, f"{name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}✓ All checks passed! Ready to start.{Colors.RESET}")
        print(f"\nNext steps:")
        print(f"  1. Backend:  cd backend && python -m venv .venv && .venv\\Scripts\\activate && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --reload")
        print(f"  2. Frontend: cd frontend && npm install && npm run dev")
        print(f"  3. Open:     http://localhost:3000")
        return 0
    else:
        print(f"\n{Colors.RED}✗ Some checks failed. Please fix the issues above.{Colors.RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
