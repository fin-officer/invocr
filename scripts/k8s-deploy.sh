#!/bin/bash
# Kubernetes deployment script

set -e

NAMESPACE="invocr"
IMAGE_TAG="1.0.0"

echo "🚀 Deploying InvOCR to Kubernetes..."

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply secrets (customize with your values)
kubectl create secret generic invocr-secrets \
  --from-literal=database-url="postgresql://user:pass@postgres:5432/invocr" \
  --from-literal=redis-url="redis://redis:6379/0" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply PVCs
kubectl apply -f kubernetes/pvc.yaml -n $NAMESPACE

# Apply deployment
kubectl apply -f kubernetes/deployment.yaml -n $NAMESPACE

# Wait for deployment
kubectl rollout status deployment/invocr-api -n $NAMESPACE

echo "✅ InvOCR deployed successfully!"
echo "🌐 Access: kubectl port-forward svc/invocr-api-service 8080:80 -n $NAMESPACE"
