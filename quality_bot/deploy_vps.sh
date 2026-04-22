#!/bin/bash
# Deployment script for Quality Bot on VPS

echo "🚀 Deploying Quality Bot to VPS..."

# Navigate to the quality_bot directory
cd ~/quality_bot

# Stop and remove existing container if it exists
echo "📦 Stopping existing container..."
docker stop quality-bot 2>/dev/null || true
docker rm quality-bot 2>/dev/null || true

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t quality-bot .

# Run the container
echo "▶️  Starting container..."
docker run -d \
  --name quality-bot \
  --restart unless-stopped \
  quality-bot

# Wait a moment for the container to start
sleep 3

# Check if container is running
echo "✅ Checking container status..."
docker ps | grep quality-bot

# Show recent logs
echo ""
echo "📋 Recent logs:"
docker logs --tail 20 quality-bot

echo ""
echo "✨ Deployment complete!"
echo "📝 To view logs: docker logs -f quality-bot"
echo "🛑 To stop: docker stop quality-bot"
echo "🔄 To restart: docker restart quality-bot"
