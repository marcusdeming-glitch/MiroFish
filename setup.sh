#!/bin/bash
# MiroFish Setup Script for Synology NAS
# Run this after uploading the MiroFish folder to your NAS

set -e

echo ""
echo "======================================"
echo "  MiroFish Setup for Synology NAS"
echo "======================================"
echo ""

# Check we are in the right folder
if [ ! -f "docker-compose.nas.yml" ]; then
    echo "ERROR: Please run this script from inside the MiroFish folder."
    echo "       cd into the MiroFish folder first, then run: bash setup.sh"
    exit 1
fi

# Check .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: No .env file found."
    echo ""
    echo "Please create a .env file in the MiroFish folder with your API keys."
    echo "You can copy the example file by running:"
    echo ""
    echo "  cp .env.example .env"
    echo ""
    echo "Then edit .env and add your LLM_API_KEY."
    exit 1
fi

# Check LLM_API_KEY is set
if grep -q "your_api_key_here" .env || ! grep -q "LLM_API_KEY=" .env; then
    echo "WARNING: LLM_API_KEY does not look set in your .env file."
    echo "         The app will not be able to run analysis without it."
    echo "         Please edit .env and set your LLM_API_KEY."
    echo ""
    read -p "Continue anyway? (y/n): " choice
    if [ "$choice" != "y" ]; then
        exit 1
    fi
fi

# Create data folder for persistent storage
echo "Creating data folder..."
mkdir -p data

# Check Docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH."
    echo "       Please install Docker via Synology Package Center first."
    exit 1
fi

echo "Building and starting MiroFish..."
echo "(First build takes 10-20 minutes — please wait)"
echo ""

# Try docker compose (DSM 7.2+) then docker-compose (older)
if docker compose version &> /dev/null 2>&1; then
    sudo docker compose -f docker-compose.nas.yml up -d --build
elif command -v docker-compose &> /dev/null; then
    sudo docker-compose -f docker-compose.nas.yml up -d --build
else
    echo "ERROR: docker compose not found."
    echo "       Please ensure Container Manager is installed from Package Center."
    exit 1
fi

echo ""
echo "======================================"
echo "  MiroFish is running!"
echo ""

# Get NAS IP
NAS_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$NAS_IP" ]; then
    echo "  Open this in your browser:"
    echo "  http://$NAS_IP:8080"
else
    echo "  Open: http://<your-NAS-IP>:8080"
fi

echo ""
echo "  Portfolio Analyzer: http://$NAS_IP:8080/portfolio"
echo "======================================"
echo ""
