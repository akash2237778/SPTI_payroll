#!/bin/bash
# Build and Push Docker Images to Docker Hub

set -e  # Exit on error

echo "🚀 Building and Pushing SPTI Payroll Docker Images"
echo "=================================================="

# Configuration
DOCKER_USERNAME="akash7778"
IMAGE_NAME_BACKEND="sptipayroll-backend"
IMAGE_NAME_CONSUMER="sptipayroll-consumer"
TAG="latest"

# Build backend
echo ""
echo "📦 Building backend image..."
docker build -t ${DOCKER_USERNAME}/${IMAGE_NAME_BACKEND}:${TAG} .

# Tag consumer (same image, different command)
echo ""
echo "📦 Tagging consumer image..."
docker tag ${DOCKER_USERNAME}/${IMAGE_NAME_BACKEND}:${TAG} ${DOCKER_USERNAME}/${IMAGE_NAME_CONSUMER}:${TAG}

# Push images
echo ""
echo "⬆️  Pushing backend image to Docker Hub..."
docker push ${DOCKER_USERNAME}/${IMAGE_NAME_BACKEND}:${TAG}

echo ""
echo "⬆️  Pushing consumer image to Docker Hub..."
docker push ${DOCKER_USERNAME}/${IMAGE_NAME_CONSUMER}:${TAG}

echo ""
echo "✅ Done! Images pushed successfully:"
echo "   - ${DOCKER_USERNAME}/${IMAGE_NAME_BACKEND}:${TAG}"
echo "   - ${DOCKER_USERNAME}/${IMAGE_NAME_CONSUMER}:${TAG}"
echo ""
echo "🎯 Next steps:"
echo "   1. Deploy on TrueNAS using docker-compose.truenas-macvlan.yml"
echo "   2. Verify consumer can reach device (192.168.2.66)"
echo "   3. Test sync from web interface"
