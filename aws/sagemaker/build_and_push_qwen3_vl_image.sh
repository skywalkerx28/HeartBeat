#!/usr/bin/env bash
set -euo pipefail

export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="heartbeat-qwen3-vl-inference"
IMAGE_TAG="latest"

if ! aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Creating ECR repository $REPO_NAME"
  aws ecr create-repository --repository-name "$REPO_NAME" --image-tag-mutability MUTABLE --region "$REGION" >/dev/null
fi

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}"

echo "Logging into Hugging Face ECR"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin 763104351884.dkr.ecr.${REGION}.amazonaws.com

echo "Logging into account ECR ${REGION}"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "Building Docker image ${ECR_URI}"
BUILDKIT_PROGRESS=plain docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -t "$ECR_URI" \
  -f infrastructure/sagemaker/docker/Dockerfile.qwen3_vl \
  .

echo "Pushing image to ECR"
docker push "$ECR_URI"

echo "Image pushed: ${ECR_URI}"
