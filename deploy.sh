#!/bin/bash

AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="226714104488"
IMAGE_NAME="finance-api"
REGISTRY_NAME="finance-app"
TAG_DOCKER="v0.0.2a-dev"
TAG_PROD="v0.0.2a"

echo "Logging in to ECR"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Building image"
docker build --no-cache --platform=linux/amd64 -t $IMAGE_NAME:$TAG_DOCKER .

echo "Tagging image"
docker tag $IMAGE_NAME:$TAG_DOCKER $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG

echo "Pushing image to ECR"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG