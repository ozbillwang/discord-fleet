# Automated Deployment with CloudFormation

## Overview

We've created a fully automated deployment pipeline using **CloudFormation** and **GitHub Actions**. Everything is Infrastructure-as-Code (IaC) - no manual AWS Console clicks needed!

---

## What Gets Deployed Automatically

### CloudFormation Stack 1: DynamoDB (`discord-fleet-dynamodb`)
- **Sessions Table**: Stores conversation history
- **Bindings Table**: Maps Discord channels to agents
- **Agents Table**: Stores agent configurations

### CloudFormation Stack 2: API Gateway & Lambda (`discord-fleet-api`)
- **API Gateway**: REST API with `/interactions` endpoint
- **Lambda: message_handler**: Receives Discord events
- **Lambda: omp_agent_handler**: Processes messages with agents
- **Lambda Layer**: Python dependencies (anthropic, openai, boto3, etc.)

---

## Deployment Process

### Step 1: Push to `feature/serverless` branch

The workflow automatically triggers when you push to the `feature/serverless` branch:

```bash
git add .
git commit -m "Deploy serverless infrastructure"
git push origin feature/serverless
```

### Step 2: GitHub Actions Runs

The workflow will:
1. ✅ **Validate** - Check Python syntax and CloudFormation templates
2. ✅ **Build Lambda Layer** - Install dependencies, create zip
3. ✅ **Deploy DynamoDB Stack** - Create tables via CloudFormation
4. ✅ **Deploy API Gateway Stack** - Create API Gateway, Lambda functions
5. ✅ **Get Webhook URL** - Extract the Discord webhook endpoint
6. ✅ **Report Status** - Display webhook URL for Discord setup

### Step 3: Watch the Workflow

1. Go to: https://github.com/ozbillwang/discord-fleet/actions
2. Click on the **"Deploy Discord Fleet Serverless (CloudFormation)"** workflow
3. Watch the logs in real-time

The workflow will output something like:

```
🌐 Discord Webhook URL:
   https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/interactions
```

### Step 4: Add Webhook URL to Discord

Once the workflow completes:

1. **Guild Manager Bot**:
   - Go to Discord Developer Portal
   - Select "BuilderXAI Guild Manager" application
   - Go to "General Information" tab
   - Find "Interactions Endpoint URL"
   - Paste the webhook URL from the workflow output
   - Click "Save Changes"

2. **Bot User Bot**:
   - Go to Discord Developer Portal
   - Select "BuilderXAI" application
   - Go to "General Information" tab
   - Find "Interactions Endpoint URL"
   - Paste the **same** webhook URL
   - Click "Save Changes"

---

## Key Benefits

✅ **Infrastructure as Code** - Entire stack in YAML files, version controlled
✅ **Repeatable** - Deploy same stack to multiple AWS accounts
✅ **Rollback** - CloudFormation can rollback failed deployments
✅ **No Manual Steps** - One push triggers entire deployment
✅ **Idempotent** - Safe to run multiple times (updates existing resources)
✅ **Auditable** - Git history shows all changes

---

## File Structure

```
serverless/
├── cloudformation/
│   ├── dynamodb-template.yaml          # DynamoDB tables
│   └── api-gateway-template.yaml       # API Gateway + Lambda
├── lambda/
│   └── llm_provider.py                 # LLM abstraction layer
└── docs/
    └── ...

.github/workflows/
└── deploy-serverless-v2.yml            # Automated deployment
```

---

## Updating the Infrastructure

If you need to make changes:

### Update DynamoDB (e.g., add a new table)

1. Edit: `serverless/cloudformation/dynamodb-template.yaml`
2. Add your new resource in the `Resources` section
3. Push to `feature/serverless`
4. GitHub Actions will update the stack

### Update Lambda Functions (e.g., change handler code)

1. Edit the inline Lambda code in: `serverless/cloudformation/api-gateway-template.yaml`
   - For `MessageHandlerFunction` → search for `Code:`
   - For `OmpAgentHandlerFunction` → search for `Code:`
2. Push to `feature/serverless`
3. GitHub Actions will update the Lambda function

### Update Lambda Permissions

1. Edit: `serverless/cloudformation/api-gateway-template.yaml`
2. Modify the `LambdaExecutionRoleArn` parameter or permissions
3. Push to `feature/serverless`
4. CloudFormation will update the stack

---

## Monitoring Deployments

### View CloudFormation Stacks

```bash
# List all stacks
aws cloudformation list-stacks \
  --region us-east-1 \
  --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE`]'

# View specific stack
aws cloudformation describe-stacks \
  --stack-name discord-fleet-dynamodb \
  --region us-east-1
```

### View Lambda Logs

```bash
# Stream logs for message_handler
aws logs tail /aws/lambda/discord-fleet-message-handler --follow

# Stream logs for omp_agent_handler
aws logs tail /aws/lambda/discord-fleet-omp-agent-handler --follow
```

### View API Gateway

```bash
# List APIs
aws apigateway get-rest-apis

# Get API details
aws apigateway get-rest-api --rest-api-id xxxxx
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| CloudFormation validation fails | Check template YAML syntax, run `aws cloudformation validate-template` |
| Lambda layer not found | Make sure S3 bucket was created and layer uploaded |
| API Gateway not deploying | Verify Lambda execution role exists and has permissions |
| Webhook URL is empty | Check CloudFormation outputs, stack may have failed |
| "ChangeSet empty" | This is normal - no changes detected from last deployment |

---

## Cost Estimate

| Service | Cost | Notes |
|---------|------|-------|
| API Gateway | $3.50/M requests | ~$0.35/day for moderate use |
| Lambda | Free (1M/month) | Then $0.20/M invocations |
| DynamoDB | $0.25/M r/w | Pay-per-request billing |
| CloudWatch Logs | $0.50/GB ingested | 7-day retention |
| **Total** | **~$5-10/month** | Very cost-efficient! |

---

## Next Steps

1. ✅ Push code to trigger deployment
2. ✅ Wait for GitHub Actions to complete
3. ✅ Copy webhook URL from workflow output
4. ✅ Add webhook URL to Discord bot applications
5. ✅ Test message routing
6. ✅ Monitor Lambda logs in CloudWatch

---

## Need Help?

If deployment fails:
1. Check GitHub Actions logs for detailed error messages
2. Check CloudFormation events: `aws cloudformation describe-stack-events --stack-name discord-fleet-api`
3. Check Lambda logs: `aws logs tail /aws/lambda/discord-fleet-message-handler --follow`
4. Verify AWS credentials are correct in GitHub Secrets

---

**Status: 🟢 READY FOR DEPLOYMENT**

Push your code to `feature/serverless` to trigger the automated deployment! 🚀
