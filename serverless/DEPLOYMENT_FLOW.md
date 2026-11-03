# Deployment Flow Diagram

## Overall Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Discord User Interaction                      │
│  (User sends message in Discord channel to bot)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Discord API                                │
│  (Routes interaction to registered webhook)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              AWS API Gateway (HTTPS Webhook)                     │
│  https://xxxxx.execute-api.region.amazonaws.com/prod/interactions│
│                                                                  │
│  - Receives POST request with Discord interaction event        │
│  - Routes to Lambda function                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│         Lambda: discord-fleet-message-handler                   │
│                                                                  │
│  1. Parse Discord interaction                                  │
│  2. Extract channel_id and message                             │
│  3. Query DynamoDB: discord-fleet-bindings                     │
│  4. Get agent_id for this channel                              │
│  5. Invoke omp_agent_handler Lambda                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│       Lambda: discord-fleet-omp-agent-handler                   │
│                                                                  │
│  1. Get agent configuration from DynamoDB                      │
│  2. Retrieve conversation history from DynamoDB                │
│  3. Prepare message with system prompt                         │
│  4. Call LLM (Claude/OpenAI/Gemini via llm_provider.py)       │
│  5. Generate response                                          │
│  6. Save to conversation history in DynamoDB                   │
│  7. Return response to message_handler                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                 DynamoDB Tables (Persistent Storage)            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ discord-fleet-sessions                                   │  │
│  │ ├─ thread_id (HASH)                                      │  │
│  │ ├─ agent_id (RANGE)                                      │  │
│  │ ├─ messages (JSON array)                                 │  │
│  │ └─ updated_at (timestamp)                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ discord-fleet-bindings                                   │  │
│  │ ├─ channel_id (HASH)                                     │  │
│  │ └─ agent_id (maps to agent)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ discord-fleet-agents                                     │  │
│  │ ├─ agent_id (HASH)                                       │  │
│  │ ├─ system_prompt (agent personality)                     │  │
│  │ ├─ model (claude-3-5-sonnet, gpt-4, etc)                │  │
│  │ └─ temperature (LLM parameter)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│       Lambda Layer: discord-fleet-dependencies                   │
│                                                                  │
│  Contains Python packages:                                      │
│  - anthropic (Claude API client)                               │
│  - openai (OpenAI API client)                                  │
│  - boto3 (AWS SDK)                                             │
│  - requests (HTTP client)                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  Developer: git push origin feature/serverless                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│       GitHub Actions Trigger                                     │
│  Event: Push to feature/serverless branch                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│       Job 1: Validate Configuration (ubuntu-latest)              │
│  ✅ Check Python syntax                                          │
│  ✅ Check file structure                                         │
│  ✅ Validate CloudFormation templates                            │
│  Duration: ~30 seconds                                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ↓                         ↓
    ┌────────────────────┐    ┌────────────────────┐
    │  Job 2: Build      │    │  (runs in parallel)│
    │  Lambda Layer      │    │                    │
    │  Duration: ~2 min  │    │                    │
    └────────────┬───────┘    │                    │
                │              │                    │
                │              └────────────────────┘
                │                    
                ↓
┌──────────────────────────────────────────────────────────────────┐
│       Job 3: Deploy Infrastructure (AWS CloudFormation)          │
│  Steps:                                                          │
│  1. Configure AWS credentials                                   │
│  2. Upload Lambda layer to S3                                   │
│  3. Create/update Lambda layer in AWS                           │
│  4. Deploy DynamoDB CloudFormation stack                        │
│     └─ discord-fleet-sessions table                            │
│     └─ discord-fleet-bindings table                            │
│     └─ discord-fleet-agents table                              │
│  5. Get Lambda execution role ARN                               │
│  6. Deploy API Gateway CloudFormation stack                     │
│     └─ REST API: discord-fleet-webhook                         │
│     └─ Lambda: discord-fleet-message-handler                   │
│     └─ Lambda: discord-fleet-omp-agent-handler                │
│     └─ API Gateway deployment to prod stage                    │
│  7. Extract webhook URL from CloudFormation outputs             │
│  Duration: ~3-4 minutes                                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│       Job 4: Notify Status                                       │
│  Display:                                                        │
│  ✅ Deployment successful                                        │
│  🌐 Webhook URL: https://xxxxx.execute-api.region.../interactions
│  📊 All stacks created/updated                                   │
│  Duration: ~10 seconds                                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│       Developer: Manual Step (Discord Configuration)             │
│  1. Copy webhook URL from workflow output                        │
│  2. Go to Discord Developer Portal                              │
│  3. Guild Manager bot → Interactions Endpoint URL → Paste       │
│  4. Bot User bot → Interactions Endpoint URL → Paste            │
│  5. Save both                                                    │
│  Duration: ~1 minute                                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│       System Ready! 🚀                                           │
│  - Discord servers connected to Lambda                          │
│  - Users can interact with bots                                 │
│  - Lambda processes messages                                     │
│  - Responses stored in DynamoDB                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## CloudFormation Stack Dependency Graph

```
┌─────────────────────────────────────────────┐
│  github-secrets (outside CloudFormation)    │
│  - AWS_ACCESS_KEY_ID                        │
│  - AWS_SECRET_ACCESS_KEY                    │
│  - DISCORD_GUILD_MANAGER_TOKEN              │
│  - DISCORD_BOT_USER_TOKEN                   │
└────────────┬────────────────────────────────┘
             │
             ↓
    ┌────────────────────┐
    │ lambda-layer       │ (manual creation via AWS CLI or Lambda publish)
    │ discord-fleet-     │
    │ dependencies       │
    └────────┬───────────┘
             │
   ┌─────────┴──────────┐
   │                    │
   ↓                    ↓
Stack 1:            Stack 2:
discord-fleet-      discord-fleet-
dynamodb            api (REST API)
│                   │
├─ Sessions table   ├─ API Gateway (REST)
├─ Bindings table   ├─ /interactions resource
└─ Agents table     ├─ POST method
                    ├─ Lambda: message-handler
                    ├─ Lambda: omp-agent-handler
                    ├─ Lambda permissions
                    └─ Deployment to prod stage

   ↓                    ↓
   └─────────┬──────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│  CloudFormation Outputs                     │
│  - Webhook URL (for Discord config)         │
│  - Lambda ARNs                              │
│  - Table names                              │
└─────────────────────────────────────────────┘
```

---

## Timeline: Full Deployment Cycle

```
T+0:00    Developer runs: git push origin feature/serverless
T+0:10    GitHub Actions workflow triggered
T+0:30    Validation job completes ✅
T+2:30    Lambda layer built and uploaded ✅
T+4:30    DynamoDB tables created ✅
T+6:00    API Gateway and Lambda functions deployed ✅
T+6:30    Workflow outputs webhook URL ✅
T+7:00    Developer copies webhook URL
T+8:00    Developer configures Discord (Guild Manager)
T+8:30    Developer configures Discord (Bot User)
T+9:00    Both bots configured and ready! 🚀
         System is live and accepting messages

Total time: ~9 minutes (mostly waiting for AWS)
User action time: ~2 minutes
Automated time: ~7 minutes
```

---

## Error Recovery Flow

```
If deployment fails:

1. Check GitHub Actions logs
   ↓
2. Identify failure (validation, build, or deploy)
   ↓
3. Fix code or CloudFormation template
   ↓
4. git add . && git commit -m "fix" && git push origin feature/serverless
   ↓
5. Workflow reruns automatically
   ↓
6. (CloudFormation is smart - it only updates changed resources)
   ↓
7. Deployment completes ✅

No manual AWS cleanup needed!
CloudFormation handles all of it.
```

---

## Monitoring During Deployment

**Real-time:**
- Watch GitHub Actions logs: https://github.com/ozbillwang/discord-fleet/actions

**Post-deployment:**
- AWS CloudFormation: `aws cloudformation describe-stack-events`
- Lambda Logs: `aws logs tail /aws/lambda/discord-fleet-message-handler --follow`
- API Gateway: `aws apigateway get-rest-api --rest-api-id xxxxx`

---

## Key Automation Points

| Step | Automated? | Tool |
|------|-----------|------|
| Code validation | ✅ | GitHub Actions + Python |
| CloudFormation validation | ✅ | AWS CloudFormation |
| Lambda layer build | ✅ | GitHub Actions |
| Lambda layer deployment | ✅ | AWS Lambda publish-layer-version |
| DynamoDB creation | ✅ | CloudFormation |
| API Gateway creation | ✅ | CloudFormation |
| Lambda function deployment | ✅ | CloudFormation |
| Permission configuration | ✅ | CloudFormation |
| Webhook URL extraction | ✅ | GitHub Actions (aws cloudformation describe-stacks) |
| Discord webhook setup | ❌ | Manual (copy-paste) |

**95% automated, 5% manual copy-paste! 🎯**
