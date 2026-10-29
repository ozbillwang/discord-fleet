# GitHub Actions - Automated Lambda Deployment

This guide explains how to use GitHub Actions to automatically deploy Discord Fleet Serverless to AWS.

## Prerequisites

You've already configured these repository variables:
- `AWS_ACCESS_KEY_ID` (variable)
- `AWS_SECRET_ACCESS_KEY` (secret)
- `AWS_DEFAULT_REGION` (variable)

## Additional Setup Required

### Step 1: Add Claude API Key to Secrets

The workflow needs access to your Claude API key. Add it as a repository secret:

1. Go to: **GitHub Repo** → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `CLAUDE_API_KEY`
4. Value: Your Claude API key (starts with `sk-ant-`)
5. Click **Add secret**

### Step 2: Create Lambda Execution IAM Role

Before deploying Lambda functions, you need to create the IAM role they'll use.

**Option A: Automatic (Recommended)**

Click the "Setup IAM Role for Lambda Execution" workflow manually:
1. Go to **Actions** tab
2. Click **Setup IAM Role for Lambda Execution**
3. Click **Run workflow**
4. Confirm AWS Account ID (leave blank to auto-detect)
5. Wait for completion

**Option B: Manual**

```bash
# Run locally if you have AWS CLI configured
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies (see setup-iam-role.yml for details)
```

## Workflow Files

### 1. `deploy-serverless.yml`

**Triggers:**
- Automatic: When you push to `feature/serverless` branch and change `serverless/**` files
- Manual: Click "Run workflow" on Actions tab

**What it does:**
1. **Validate** - Check Python syntax and file structure
2. **Build Lambda Layer** - Package Python dependencies (anthropic, openai, boto3, etc.)
3. **Package Lambda Functions** - Create message_handler and omp_agent_handler functions
4. **Deploy to AWS** - Upload everything to AWS and create resources
5. **Notify** - Report deployment status

**Output:**
- Lambda Layer version
- Lambda function names
- DynamoDB table names
- S3 bucket for artifacts

### 2. `setup-iam-role.yml`

**Triggers:**
- Manual only: Click "Run workflow" on Actions tab

**What it does:**
1. Creates `lambda-execution-role` IAM role
2. Attaches necessary policies:
   - DynamoDB read/write
   - Lambda invoke
   - CloudWatch Logs
   - Secrets Manager access

## How to Deploy

### First Time Setup

1. Ensure all secrets are configured:
   ```bash
   # Check in GitHub:
   # Settings → Secrets and variables → Actions
   # Should have:
   # - AWS_ACCESS_KEY_ID (variable)
   # - AWS_SECRET_ACCESS_KEY (secret)
   # - AWS_DEFAULT_REGION (variable)
   # - CLAUDE_API_KEY (secret)
   ```

2. Create IAM role:
   ```
   Go to Actions → "Setup IAM Role for Lambda Execution" → Run workflow
   ```

3. Deploy Lambda functions:
   ```bash
   # Option A: Push code to feature/serverless
   git push origin feature/serverless
   
   # Option B: Manually trigger
   # Go to Actions → "Deploy Discord Fleet Serverless" → Run workflow
   ```

### Subsequent Deployments

After the initial setup, just push to `feature/serverless`:

```bash
git add serverless/
git commit -m "Update Lambda functions"
git push origin feature/serverless
```

The workflow will automatically:
1. Validate changes
2. Build new Lambda layer (if dependencies changed)
3. Package updated functions
4. Deploy to AWS
5. Report status

## Monitoring Deployments

### In GitHub

1. Go to **Actions** tab
2. Click the workflow run
3. Watch real-time progress
4. Check logs for any errors

### In AWS

After deployment, verify resources exist:

```bash
# Check Lambda functions
aws lambda list-functions --region us-east-1 | grep discord-fleet

# Check DynamoDB tables
aws dynamodb list-tables --region us-east-1 | grep discord-fleet

# Check Lambda layers
aws lambda list-layer-versions --layer-name discord-fleet-dependencies --region us-east-1
```

## Environment Variables Used by Lambda

The workflow sets these environment variables for Lambda functions:

**message_handler:**
- `OMP_AGENT_HANDLER` - ARN of omp_agent_handler function
- `BINDINGS_TABLE` - DynamoDB table name

**omp_agent_handler:**
- `AGENTS_TABLE` - DynamoDB table name
- `SESSIONS_TABLE` - DynamoDB table name
- `LLM_API_KEY` - Claude API key (from secrets)

To add more environment variables, edit the workflow:

```yaml
--environment Variables="{VAR_NAME=value,VAR_NAME2=value2}"
```

## Troubleshooting

### Deployment Fails with "Role not found"

**Cause:** Lambda execution role doesn't exist

**Solution:**
1. Run "Setup IAM Role for Lambda Execution" workflow first
2. Wait for completion
3. Then run main deployment workflow

### "Access Denied" when creating DynamoDB tables

**Cause:** AWS credentials lack DynamoDB permissions

**Solution:**
1. Verify `AWS_SECRET_ACCESS_KEY` is correct
2. Ensure AWS user has `dynamodb:CreateTable` permission
3. Check AWS region is correct

### Lambda functions timeout or fail

**Cause:** Missing Lambda layer or environment variables

**Solution:**
1. Check workflow logs for layer version
2. Verify function environment variables in AWS Lambda console
3. Check CloudWatch Logs for function errors

### "Invalid zip" error for Lambda

**Cause:** Artifact extraction failed

**Solution:**
1. Check workflow logs during "Extract artifacts" step
2. Verify `lambda-functions.zip` was created successfully
3. Re-run workflow

## Customization

### Change AWS Region

Edit variables in GitHub Settings:
```
AWS_DEFAULT_REGION = us-west-2  (or your preferred region)
```

### Add More Lambda Functions

1. Add function code in workflow under "Create lambda packages" step
2. Add zip and create-function commands for new function
3. Push to `feature/serverless`

### Modify DynamoDB Tables

Edit the "Create DynamoDB Tables" step in `deploy-serverless.yml`

### Add Additional Environment Variables

Edit the `--environment Variables="{...}"` sections for each function

## Cost Monitoring

GitHub Actions minutes are free for public repos, but AWS resources have costs:

- **Lambda:** $0.20 per 1M requests + compute time
- **DynamoDB:** $1.25 per 1M on-demand requests
- **S3:** $0.023 per GB stored

Set up AWS Budgets to alert if costs exceed threshold:

```bash
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

## Next Steps

1. ✅ Configure all secrets in GitHub Settings
2. ✅ Run "Setup IAM Role for Lambda Execution" workflow
3. ✅ Push code to `feature/serverless` to trigger deployment
4. ✅ Monitor Actions tab for deployment progress
5. ✅ Verify resources in AWS Console
6. ✅ Test Lambda functions via AWS Lambda console

## Support

If deployment fails:
1. Check GitHub Actions logs
2. Check AWS CloudFormation events (if using CF)
3. Check CloudWatch Logs for Lambda errors
4. Verify all secrets are configured
5. Verify IAM role has correct permissions
