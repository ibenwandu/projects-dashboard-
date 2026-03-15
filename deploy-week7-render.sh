#!/bin/bash

# Week 7 Render Deployment Script
# Deploys Celery Beat + Worker services for email automation
# Usage: ./deploy-week7-render.sh
# Requirements: curl, RENDER_API_KEY environment variable

set -e

echo "🚀 Week 7 Email Automation - Render Deployment"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    if ! command -v curl &> /dev/null; then
        echo -e "${RED}❌ curl is required but not installed${NC}"
        exit 1
    fi

    if [ -z "$RENDER_API_KEY" ]; then
        echo -e "${RED}❌ RENDER_API_KEY environment variable not set${NC}"
        echo "   Get your API key from: https://dashboard.render.com/account/api-tokens"
        echo "   Then run: export RENDER_API_KEY='your-key-here'"
        exit 1
    fi

    echo -e "${GREEN}✓ Prerequisites met${NC}"
    echo ""
}

# Get service details
get_service_details() {
    echo -e "${BLUE}Fetching service details...${NC}"

    # Get list of services - adjust the service query as needed
    SERVICES=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services?name=emy" \
        -H "Content-Type: application/json")

    echo "Services found:"
    echo "$SERVICES" | head -20
}

# Trigger deployment
deploy_services() {
    echo -e "${BLUE}Triggering deployment of Week 7 services...${NC}"
    echo ""

    # Service IDs (you need to set these from your Render dashboard)
    BEAT_SERVICE_ID="${BEAT_SERVICE_ID:-emy-celery-beat}"
    WORKER_SERVICE_ID="${WORKER_SERVICE_ID:-emy-celery-worker}"
    GATEWAY_SERVICE_ID="${GATEWAY_SERVICE_ID:-emy-phase1a}"
    BRAIN_SERVICE_ID="${BRAIN_SERVICE_ID:-emy-brain}"

    echo "Services to deploy:"
    echo "  1. $BEAT_SERVICE_ID (Celery Beat)"
    echo "  2. $WORKER_SERVICE_ID (Celery Workers)"
    echo "  3. $GATEWAY_SERVICE_ID (Gateway)"
    echo "  4. $BRAIN_SERVICE_ID (Brain)"
    echo ""

    # Deploy Celery Beat
    echo -e "${BLUE}→ Deploying $BEAT_SERVICE_ID...${NC}"
    BEAT_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$BEAT_SERVICE_ID/deploys" \
        -H "Content-Type: application/json" \
        -d '{}' || echo "failed")

    if [[ $BEAT_RESPONSE == *"failed"* ]] || [[ -z $BEAT_RESPONSE ]]; then
        echo -e "${RED}❌ Failed to trigger Beat service deployment${NC}"
        echo "   This may be expected if service IDs are incorrect"
    else
        echo -e "${GREEN}✓ Beat service deployment triggered${NC}"
    fi

    # Deploy Celery Workers
    echo -e "${BLUE}→ Deploying $WORKER_SERVICE_ID...${NC}"
    WORKER_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$WORKER_SERVICE_ID/deploys" \
        -H "Content-Type: application/json" \
        -d '{}' || echo "failed")

    if [[ $WORKER_RESPONSE == *"failed"* ]] || [[ -z $WORKER_RESPONSE ]]; then
        echo -e "${RED}❌ Failed to trigger Worker service deployment${NC}"
    else
        echo -e "${GREEN}✓ Worker service deployment triggered${NC}"
    fi

    # Optionally redeploy Gateway and Brain for consistency
    echo ""
    echo -e "${BLUE}→ Redeploying existing services for consistency...${NC}"

    curl -s -X POST \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$GATEWAY_SERVICE_ID/deploys" \
        -H "Content-Type: application/json" \
        -d '{}' > /dev/null 2>&1 || true

    curl -s -X POST \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$BRAIN_SERVICE_ID/deploys" \
        -H "Content-Type: application/json" \
        -d '{}' > /dev/null 2>&1 || true

    echo -e "${GREEN}✓ Deployment requests submitted${NC}"
}

# Monitor deployment
monitor_deployment() {
    echo ""
    echo -e "${BLUE}Monitoring deployment status...${NC}"
    echo "Check progress at: https://dashboard.render.com"
    echo ""
    echo "Services should be live in 3-5 minutes"
    echo ""
}

# Post-deployment checks
post_deployment_checks() {
    echo -e "${BLUE}Post-Deployment Verification${NC}"
    echo ""

    # Wait a bit for services to start
    echo "Waiting for services to start (30 seconds)..."
    sleep 30

    # Check Gateway health
    echo -e "${BLUE}→ Checking Gateway health...${NC}"
    GATEWAY_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
        https://emy-phase1a.onrender.com/health || echo "000")

    if [ "$GATEWAY_HEALTH" = "200" ]; then
        echo -e "${GREEN}✓ Gateway is healthy (HTTP $GATEWAY_HEALTH)${NC}"
    else
        echo -e "${RED}❌ Gateway health check failed (HTTP $GATEWAY_HEALTH)${NC}"
    fi

    # Check polling status endpoint
    echo -e "${BLUE}→ Checking polling status...${NC}"
    POLLING_STATUS=$(curl -s https://emy-phase1a.onrender.com/emails/polling-status)

    if [[ $POLLING_STATUS == *"status"* ]]; then
        echo -e "${GREEN}✓ Polling status endpoint is responding${NC}"
        echo "   Response: $POLLING_STATUS" | head -c 100
        echo ""
    else
        echo -e "${RED}❌ Polling status endpoint not responding${NC}"
    fi

    echo ""
}

# Main execution
main() {
    check_prerequisites
    echo -e "${BLUE}Note: Render CLI not available, using API method${NC}"
    echo "If you prefer manual deployment, visit:"
    echo "  → https://dashboard.render.com"
    echo "  → Select your project"
    echo "  → Click Deploy"
    echo ""

    # Try API deployment
    if [ ! -z "$RENDER_API_KEY" ]; then
        deploy_services
        monitor_deployment

        # Wait and check
        echo "Waiting 60 seconds before checking status..."
        sleep 60
        post_deployment_checks
    fi

    echo ""
    echo -e "${GREEN}✓ Deployment process initiated${NC}"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Monitor logs on Render dashboard"
    echo "  2. Verify all 4 services are 'Live' (3-5 minutes)"
    echo "  3. Check /emails/polling-status endpoint"
    echo "  4. Send test email to configured Gmail"
    echo ""
    echo "📖 Full guide: see WEEK7_RENDER_DEPLOYMENT.md"
}

main "$@"
