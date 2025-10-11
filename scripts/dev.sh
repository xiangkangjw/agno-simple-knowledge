#!/bin/bash

# Development startup script for Knowledge Management System

echo "🚀 Starting Knowledge Management System in Development Mode"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python first."
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo "📦 Installing Node.js dependencies..."
npm install

echo ""
echo "🐍 Installing Python dependencies..."
cd python-backend
$PYTHON_CMD -m pip install -r requirements.txt
cd ..

echo ""
echo "🔧 Starting development environment..."
echo "   - Tauri app will start automatically"
echo "   - Python backend will be managed by Tauri"
echo "   - Hot reload is enabled for frontend changes"
echo ""

# Start the Tauri development server
npm run tauri:dev