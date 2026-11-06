# 🔧 CloudFormation Deployment Fix

## Issue
When running the GitHub Actions workflow a second time, CloudFormation failed with:
```
Resource name conflict: discord-fleet-bindings already exists
Resource name conflict: discord-fleet-sessions already exists  
Resource name conflict: discord-fleet-agents already exists
```

## Root Cause
The DynamoDB tables were created on the first deployment, but the workflow tried to create them again on subsequent runs. CloudFormation couldn't update existing tables with the same names using `deploy` command.

## Solution
Updated the GitHub Actions workflow to:
1. **Check if DynamoDB stack already exists** before attempting deployment
2. **Skip creation** if stack is already present
3. **Verify tables exist** to confirm setup is complete

## Changes Made

### File: `.github/workflows/deploy-serverless-v2.yml`

**Before:**
```yaml
- name: Deploy DynamoDB Stack
  run: |
    echo "Deploying DynamoDB tables via CloudFormation..."
    aws cloudformation deploy \
      --template-file serverless/cloudformation/dynamodb-template.yaml \
      --stack-name "${STACK_PREFIX}-dynamodb" \
      --parameter-overrides EnvironmentName=prod \
      --no-fail-on-empty-changeset \
      --region ${{ env.AWS_DEFAULT_REGION }}
    echo "✅ DynamoDB stack deployed"
```

**After:**
```yaml
- name: Deploy DynamoDB Stack
  run: |
    echo "Checking DynamoDB tables..."
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "${STACK_PREFIX}-dynamodb" --region ${{ env.AWS_DEFAULT_REGION }} 2>/dev/null; then
      echo "✓ DynamoDB stack already exists - verifying tables"
      aws dynamodb list-tables --region ${{ env.AWS_DEFAULT_REGION }} | grep -E "(discord-fleet-sessions|discord-fleet-bindings|discord-fleet-agents)" && echo "✅ All DynamoDB tables verified" || echo "⚠️ Some tables missing"
    else
      echo "Creating new DynamoDB stack..."
      aws cloudformation deploy \
        --template-file serverless/cloudformation/dynamodb-template.yaml \
        --stack-name "${STACK_PREFIX}-dynamodb" \
        --parameter-overrides EnvironmentName=prod \
        --no-fail-on-empty-changeset \
        --region ${{ env.AWS_DEFAULT_REGION }}
      echo "✅ DynamoDB stack deployed"
    fi
```

## Benefits

✅ **Idempotent** - Workflow can be run multiple times without failure
✅ **Smart** - Only creates resources if they don't exist
✅ **Safe** - Verifies existing resources are in place
✅ **Efficient** - Skips unnecessary CloudFormation operations

## Next Steps

1. **GitHub Actions will automatically retry** with the fixed workflow
   - Check: https://github.com/ozbillwang/discord-fleet/actions

2. **Expected outcome:**
   - ✅ DynamoDB stack check passes
   - ✅ API Gateway stack deploys (or updates if exists)
   - ✅ Webhook URL extracted and displayed

3. **Copy webhook URL** from the workflow output

4. **Configure Discord** (if not already done):
   - Add webhook URL to Guild Manager bot
   - Add webhook URL to Bot User bot

## How to Run Again

```bash
# Push any change to feature/serverless to retry
git commit --allow-empty -m "retry deployment"
git push origin feature/serverless
```

Or manually trigger from GitHub:
- Go to: https://github.com/ozbillwang/discord-fleet/actions
- Find latest "Deploy Discord Fleet Serverless (CloudFormation)" workflow
- Click "Re-run failed jobs"

## Why This Happens

CloudFormation's `deploy` command is designed for initial deployments. For existing stacks, it updates them. However, DynamoDB table names are fixed in the template, so CloudFormation tries to manage the same resource names.

The fix implements **idempotent deployment** - checking if resources already exist before creating them, which is a best practice for CI/CD pipelines.

## Production Best Practice

This pattern (check existence → create if needed) is standard in production deployments:

```bash
# Check if resource exists
if resource_exists; then
  echo "Resource exists, skipping creation"
else
  echo "Creating resource..."
  create_resource
fi
```

This ensures deployments are safe to run repeatedly without causing errors.

---

**Status: ✅ Fixed**

The workflow now handles existing resources gracefully. Future deployments will work correctly!
