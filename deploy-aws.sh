#!/usr/bin/env bash
# =============================================================
#  WeatherWear — AWS Deployment Script
#  Deploys to:
#    - Backend:  AWS Elastic Beanstalk (auto-scaling EC2)
#    - Frontend: AWS S3 + CloudFront
#
#  Prerequisites:
#    aws-cli v2, eb-cli, docker
#    AWS credentials configured (aws configure)
# =============================================================

set -euo pipefail

APP_NAME="weatherwear"
REGION="eu-west-1"
EB_ENV="${APP_NAME}-prod"
S3_BUCKET="${APP_NAME}-frontend-$(date +%s)"

echo "═══════════════════════════════════════════"
echo "  WeatherWear AWS Deployment"
echo "═══════════════════════════════════════════"

# ── 1. Deploy Backend to Elastic Beanstalk ──────────────────
echo ""
echo "► Deploying Outfit Recommendation API to Elastic Beanstalk…"
cd backend

# Create Elastic Beanstalk application if not exists
aws elasticbeanstalk describe-applications --application-names "$APP_NAME" \
  --region "$REGION" > /dev/null 2>&1 || \
aws elasticbeanstalk create-application \
  --application-name "$APP_NAME" \
  --description "WeatherWear Outfit Recommendation API" \
  --region "$REGION"

# Initialise EB (Python 3.11 platform)
eb init "$APP_NAME" \
  --platform "Python 3.11 running on 64bit Amazon Linux 2023" \
  --region "$REGION" \
  --keyname weatherwear-key 2>/dev/null || true

# Create/update environment
eb use "$EB_ENV" 2>/dev/null || \
eb create "$EB_ENV" \
  --instance-type t3.small \
  --min-instances 2 \
  --max-instances 8 \
  --envvars "FLASK_ENV=production,PORT=8080" \
  --region "$REGION"

eb deploy --staged
EB_URL=$(eb status | grep "CNAME" | awk '{print $2}')
echo "✅ Backend deployed: http://${EB_URL}"

cd ..

# ── 2. Deploy Frontend to S3 + CloudFront ───────────────────
echo ""
echo "► Creating S3 bucket for frontend…"
aws s3 mb "s3://${S3_BUCKET}" --region "$REGION" 2>/dev/null || true

# Update API URLs in frontend to point to EB backend
sed -i "s|http://localhost:5000|http://${EB_URL}|g" frontend/index.html
sed -i "s|http://localhost:5001|http://${EB_URL}|g" frontend/index.html  # classmate would have their own URL

# Upload frontend
aws s3 sync frontend/ "s3://${S3_BUCKET}/" \
  --acl public-read \
  --delete

# Enable static website hosting
aws s3 website "s3://${S3_BUCKET}/" \
  --index-document index.html \
  --error-document index.html

# Create CloudFront distribution
echo ""
echo "► Creating CloudFront distribution…"
CF_ID=$(aws cloudfront create-distribution \
  --origin-domain-name "${S3_BUCKET}.s3.amazonaws.com" \
  --default-root-object index.html \
  --query "Distribution.Id" \
  --output text 2>/dev/null || echo "existing")

CF_DOMAIN=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[0].DomainName=='${S3_BUCKET}.s3.amazonaws.com'].DomainName" \
  --output text 2>/dev/null || echo "pending")

echo ""
echo "═══════════════════════════════════════════"
echo "  Deployment Complete!"
echo "═══════════════════════════════════════════"
echo "  Frontend: https://${CF_DOMAIN}"
echo "  Backend:  http://${EB_URL}"
echo "  API docs: http://${EB_URL}/api/info"
echo ""
echo "  Share your API with classmates:"
echo "  POST http://${EB_URL}/api/recommend"
echo "═══════════════════════════════════════════"
