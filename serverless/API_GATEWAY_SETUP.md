# API Gateway & Discord Webhooks Setup

## Overview

Discord sends interaction events (slash commands, button clicks, message events) to our Lambda functions via **HTTP webhooks**. We need to set up **AWS API Gateway** to receive these events.

---

## Step 1: Create API Gateway

### 1.1 Go to AWS Console

1. Open: https://console.aws.amazon.com/apigateway
2. Click **"Create API"**
3. Choose **"REST API"** (not HTTP API)
4. Click **"Build"**

### 1.2 Create API

1. **API name**: `discord-fleet-webhook`
2. **Description**: Discord interaction webhooks for Discord Fleet
3. **Endpoint type**: Regional
4. Click **"Create API"**

---

## Step 2: Create Resources & Methods

### 2.1 Create `/interactions` Resource

1. Click on **"/"** (root resource)
2. Click **"Create Resource"**
3. **Resource name**: `interactions`
4. **Resource path**: `/interactions`
5. Click **"Create Resource"**

### 2.2 Create POST Method

1. Select the `/interactions` resource
2. Click **"Create Method"**
3. Select **POST**
4. Click **"Create"**

### 2.3 Configure Lambda Integration

1. **Integration type**: Lambda Function
2. **Lambda Function**: Select your region and function name
3. For now, select: `discord-fleet-message-handler` (we'll create this)
4. Click **"Save"**
5. When prompted, click **"OK"** to grant permissions

---

## Step 3: Enable CORS (if needed)

1. Select the `/interactions` resource
2. Click **"Enable CORS"**
3. Keep default settings
4. Click **"Enable CORS and replace existing CORS headers"**

---

## Step 4: Deploy API

1. Click **"Deploy API"** (top button)
2. **Deployment stage**: Create new stage
3. **Stage name**: `prod`
4. Click **"Deploy"**

### Get Your Webhook URL

After deployment, you'll see:
```
Invoke URL: https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod/interactions
```

**Save this URL!** This is where Discord will send events.

---

## Step 5: Configure Discord Webhook

For each bot, we need to tell Discord to send events to our API Gateway URL.

### 5.1 Guild Manager Bot Webhook

1. Go to Discord Developer Portal
2. Select **Guild Manager bot** application
3. Go to **General Information** tab
4. Find **"Interactions Endpoint URL"** field
5. Paste your API Gateway URL: `https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod/interactions`
6. Click **"Save Changes"**

Discord will test the endpoint - it should return a 200 response.

### 5.2 Bot User Bot Webhook

1. Go to Discord Developer Portal
2. Select **Bot User bot** application
3. Go to **General Information** tab
4. Find **"Interactions Endpoint URL"** field
5. Paste the **SAME** API Gateway URL
6. Click **"Save Changes"**

---

## Step 6: Verify Lambda Functions are Deployed

Make sure these Lambda functions exist in AWS:
- `discord-fleet-message-handler`
- `discord-fleet-omp-agent-handler`

If they don't exist, we need to deploy them first.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Failed to save" in Discord | Check API Gateway URL is correct and returns 200 |
| "Endpoint URL verification failed" | Lambda must return proper Discord verification response |
| "Invalid Interactions Endpoint URL" | Make sure URL starts with `https://` |
| API Gateway returns 502 error | Check Lambda function exists and has correct permissions |

---

## Next Steps

1. Deploy the Lambda functions (message_handler, omp_agent_handler)
2. Test with a Discord slash command
3. Verify message routing works

---

## Architecture Diagram

```
Discord Server
    ↓ (interaction event)
Discord API
    ↓ (HTTP POST to webhook URL)
API Gateway (/interactions endpoint)
    ↓ (invokes Lambda)
Lambda: message_handler
    ↓ (calls)
Lambda: omp_agent_handler
    ↓ (reads/writes)
DynamoDB (sessions, bindings, agents)
    ↓ (response)
Discord API
    ↓ (sends reply)
Discord Server
```

---

## Cost Estimate

- API Gateway: ~$3.50/million requests
- Lambda invocations: Included in AWS free tier (1M/month)
- DynamoDB: Pay-per-request (~$0.25/million reads)

Total monthly cost: $5-10 for moderate usage
