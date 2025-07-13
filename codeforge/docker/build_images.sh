#!/bin/bash

# Build all CodeForge Docker images

set -e

echo "Building CodeForge Docker images..."

# Python image
echo "Building Python 3.11 image..."
docker build -t codeforge/python:3.11 ./images/python/

# Node.js image
echo "Building Node.js 20 image..."
docker build -t codeforge/node:20 ./images/node/

# Go image
echo "Building Go 1.21 image..."
docker build -t codeforge/go:1.21 ./images/go/

# Ubuntu base image
echo "Building Ubuntu base image..."
docker build -t codeforge/ubuntu:latest ./images/ubuntu/

echo "All images built successfully!"

# List built images
echo -e "\nBuilt images:"
docker images | grep codeforge