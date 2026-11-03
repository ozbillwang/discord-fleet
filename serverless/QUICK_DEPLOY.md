# Quick Deploy Guide (5 Minutes)

## Status Check

Before deploying, make sure you have:

- ✅ Guild Manager bot token in GitHub Secrets (`DISCORD_GUILD_MANAGER_TOKEN`)
- ✅ Bot User bot token in GitHub Secrets (`DISCORD_BOT_USER_TOKEN`)
- ✅ AWS credentials in GitHub Secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- ✅ AWS region in GitHub Variables (`AWS_DEFAULT_REGION`)
- ✅ Both bots added to your Discord server

---

## 1. Trigger Deployment (1 minute)

```bash
# Navigate to repo
cd /path/to/discord-fleet

# Create/switch to feature/serverless branch
git checkout -b feature/serverless

# Stage all changes
git add .

# Commit
git commit -m "Deploy Discord Fleet serverless infrastructure with CloudFormation"

# Push to trigger GitHub Actions
git push origin feature/serverless
```

---

## 2. Monitor Deployment (3 minutes)

1. Go to: https://github.com/ozbillwang/discord-fleet/actions
2. Click **"Deploy Discord Fleet Serverless (CloudFormation)"**
3. Watch the workflow run
4. Wait for it to complete (usually 3-5 minutes)

**Look for the output section that shows:**
```
🌐 Discord Webhook URL:
   https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/interactions
```

---

## 3. Add Webhook to Discord (1 minute)

Copy the webhook URL from the workflow output, then:

### For Guild Manager Bot:
1. Go to https://discord.com/developers/applications
2. Select **"BuilderXAI Guild Manager"**
3. Click **"General Information"** (left sidebar)
4. Find **"Interactions Endpoint URL"**
5. Paste the webhook URL
6. Click **"Save Changes"**

### For Bot User Bot:
1. Select **"BuilderXAI"** application
2. Click **"General Information"**
3. Find **"Interactions Endpoint URL"**
4. Paste the **same** webhook URL
5. Click **"Save Changes"**

---

## 4. Verify Deployment

**Check CloudFormation stacks:**
```bash
aws cloudformation describe-stacks \
  --region us-east-1 \
  --query 'Stacks[?starts_with(StackName, `discord-fleet`)]'
```

**Check Lambda functions:**
```bash
aws lambda list-functions \
  --region us-east-1 \
  --query 'Functions[?starts_with(FunctionName, `discord-fleet`)]'
```

**Check API Gateway:**
```bash
aws apigateway get-rest-apis \
  --region us-east-1 \
  --query 'items[?name==`discord-fleet-webhook`]'
```

---

## 5. Test the Connection

Send a test message in Discord to one of your bots:
- Type: `/test` or just send a regular message
- Check CloudWatch Logs: `aws logs tail /aws/lambda/discord-fleet-message-handler --follow`
- Verify bot responds

---

## That's It! 🎉

Your Discord Fleet serverless infrastructure is now deployed!

---

## Troubleshooting

### Deployment Failed?
- Check GitHub Actions logs for detailed error
- Look at CloudFormation events: `aws cloudformation describe-stack-events --stack-name discord-fleet-api`
- Verify AWS credentials are correct

### Webhook URL not working?
- Check Lambda logs: `aws logs tail /aws/lambda/discord-fleet-message-handler --follow`
- Verify webhook URL is correct in Discord Developer Portal
- Make sure it starts with `https://`

### Discord says "Invalid Endpoint URL"?
- Wait 30 seconds (Discord caches this)
- Try again
- Check that Lambda is returning proper Discord response format

---

## What Got Deployed

| Component | Type | Details |
|-----------|------|---------|
| discord-fleet-sessions | DynamoDB Table | Stores conversation history |
| discord-fleet-bindings | DynamoDB Table | Maps channels to agents |
| discord-fleet-agents | DynamoDB Table | Stores agent configs |
| discord-fleet-webhook | API Gateway | Receives Discord events |
| discord-fleet-message-handler | Lambda | Processes messages |
| discord-fleet-omp-agent-handler | Lambda | Handles agent logic |
| discord-fleet-dependencies | Lambda Layer | Python dependencies |

---

## Next Steps

1. Test message routing
2. Configure channel bindings in DynamoDB
3. Set up agent personalities
4. Integrate with Claude/OpenAI/Gemini
5. Deploy to production

---

**Need more details?** See [AUTOMATED_DEPLOYMENT.md](AUTOMATED_DEPLOYMENT.md)
