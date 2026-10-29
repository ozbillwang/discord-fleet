# Quick Start: Deploy Discord Fleet Lambda via GitHub Actions

## 🚀 In 5 Minutes

### Step 1: Add Claude API Key Secret (2 minutes)

```bash
# In GitHub:
1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: CLAUDE_API_KEY
4. Value: sk-ant-YOUR_KEY_HERE
5. Add secret
```

### Step 2: Create IAM Role (2 minutes)

```bash
# In GitHub Actions:
1. Go to Actions tab
2. Find "Setup IAM Role for Lambda Execution"
3. Click "Run workflow"
4. Wait for ✅ (should be <1 minute)
```

### Step 3: Deploy Lambda (1 minute)

```bash
# Just push to feature/serverless:
cd /path/to/discord-fleet
git push origin feature/serverless

# Or manually trigger:
# Actions → Deploy Discord Fleet Serverless → Run workflow
```

## ✅ What Gets Deployed

After the workflow completes, you'll have:

- ✅ **Lambda Functions:**
  - `discord-fleet-message-handler` - Routes Discord messages
  - `discord-fleet-omp-agent-handler` - Processes with LLM

- ✅ **DynamoDB Tables:**
  - `discord-fleet-sessions` - Conversation history
  - `discord-fleet-bindings` - Channel → agent mappings
  - `discord-fleet-agents` - Agent configurations

- ✅ **Lambda Layer:**
  - `discord-fleet-dependencies` - Python packages (anthropic, openai, boto3)

- ✅ **S3 Bucket:**
  - Stores deployment artifacts

## 🔍 Monitor Deployment

Watch real-time progress in GitHub Actions:

1. Go to **Actions** tab
2. Click the running workflow
3. Expand steps to see logs
4. Green checkmark = success, red X = failure

## 📊 Verify in AWS Console

After deployment succeeds:

```bash
# Check Lambda functions exist:
aws lambda list-functions --region us-east-1 \
  | grep discord-fleet

# Check DynamoDB tables exist:
aws dynamodb list-tables --region us-east-1 \
  | grep discord-fleet

# Check Lambda layer version:
aws lambda list-layer-versions \
  --layer-name discord-fleet-dependencies \
  --region us-east-1
```

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Role not found"** | Run "Setup IAM Role" workflow first |
| **"Access Denied"** | Check AWS credentials in GitHub secrets |
| **Deployment hangs** | Check GitHub Actions logs for specific error |
| **Lambda timeout** | Increase timeout in function configuration |

## 🎯 Next: Configure Discord

Once Lambda is deployed, you need:

1. Create Discord bot applications (2 apps needed)
2. Get bot tokens
3. Add webhook URL to Discord
4. Test message routing

See `../SETUP_REQUIREMENTS.md` for Discord setup.

## 📝 Customize Before Deployment

Edit these before pushing:

### Add environment variables

In `.github/workflows/deploy-serverless.yml`:

```yaml
--environment Variables="{
  MY_VAR=value,
  ANOTHER_VAR=value2
}"
```

### Change AWS region

In GitHub Settings → Variables:
```
AWS_DEFAULT_REGION = us-west-2
```

### Add new Lambda functions

1. Create function code in workflow
2. Add create-function command
3. Push to `feature/serverless`

## 🔐 Security Best Practices

✅ Do:
- Keep AWS credentials secret (use GitHub secrets)
- Use IAM role with minimal permissions
- Enable CloudWatch logging
- Monitor costs

❌ Don't:
- Commit AWS credentials to git
- Use root AWS credentials
- Skip IAM role setup
- Ignore deployment errors

## 📈 Scaling Up

After initial deployment:

1. **Add more agents** - Update DynamoDB agents table
2. **Add Discord servers** - Add bindings for new channels
3. **Monitor costs** - Set AWS budgets
4. **Update code** - Push to feature/serverless
5. **Add tests** - Include test step in workflow

## 🎓 Learn More

- Full setup: `GITHUB_ACTIONS_SETUP.md`
- Workflow details: `.github/workflows/deploy-serverless.yml`
- AWS resources: Check AWS Console

---

**That's it! Your Discord Fleet Lambda is now deployed!** 🎉

Next: Set up Discord bot and test message routing.
