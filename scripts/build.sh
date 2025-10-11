#!/bin/bash

# Production build script for Knowledge Management System

echo "🏗️  Building Knowledge Management System for Production"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

echo "📦 Installing dependencies..."
npm install

echo ""
echo "🔨 Building frontend..."
npm run build

echo ""
echo "🦀 Building Tauri application..."
npm run tauri:build

echo ""
echo "✅ Build complete! Check the src-tauri/target/release directory for the built application."