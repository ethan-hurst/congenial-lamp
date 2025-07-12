#!/bin/bash
# Build all Docker images for CodeForge

set -e

echo "Building CodeForge Docker images..."

# Change to docker directory
cd "$(dirname "$0")/../docker"

# Build base image
echo "Building base image..."
docker build -t codeforge/base:latest ./base

# Build language images
echo "Building Python image..."
docker build -t codeforge/python:latest ./python

echo "Building Node.js image..."
docker build -t codeforge/node:latest ./node

echo "Building Go image..."
docker build -t codeforge/go:latest ./go

echo "Building Rust image..."
docker build -t codeforge/rust:latest ./rust

# Build orchestrator
echo "Building orchestrator image..."
cd ../backend
docker build -t codeforge/orchestrator:latest .

echo "All images built successfully!"

# Tag images with version
VERSION=$(date +%Y%m%d-%H%M%S)
for image in base python node go rust orchestrator; do
    docker tag codeforge/$image:latest codeforge/$image:$VERSION
done

echo "Images tagged with version: $VERSION"