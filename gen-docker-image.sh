#!/bin/bash
set -e

# Check if the Dockerfile exists
if [ ! -f Dockerfile ]; then
    echo "Dockerfile not found!"
    exit 1
fi

# Check if the version argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# Get the version from the first argument
VERSION=$1

# Build the Docker image
docker build -t aasatorres/server-saude:$VERSION .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Docker image aasatorres/server-saude:$VERSION built successfully."
else
    echo "Docker image build failed."
    exit 1
fi

# Push the Docker image to the repository
docker push aasatorres/server-saude:$VERSION
# Check if the push was successful
if [ $? -eq 0 ]; then   
    echo "Docker image aasatorres/server-saude:$VERSION pushed successfully."
else
    echo "Docker image push failed."
    exit 1
fi