# 🔧 Lambda Handler Parameter Fix

## Issue
CloudFormation deployment failed with:
```
Resource handler returned message: "Runtime and Handler are mandatory parameters 
for functions created with deployment packages."
```

Affected Lambda functions:
- ❌ MessageHandlerFunction
- ❌ OmpAgentHandlerFunction

## Root Cause
When creating AWS Lambda functions with inline code (`ZipFile`), CloudFormation requires:
1. **Runtime** - ✅ Was present (python3.11)
2. **Handler** - ❌ **Missing!**

The `Handler` parameter tells Lambda which function to execute when invoked.

Format: `filename.function_name`
- In our case: `index.lambda_handler` (the function is named `lambda_handler` in the inline code)

## Solution
Added the missing `Handler` parameter to both Lambda functions:

```yaml
# Before
Runtime: python3.11
Role: !Ref LambdaExecutionRoleArn

# After  
Runtime: python3.11
Handler: index.lambda_handler    # ← ADDED
Role: !Ref LambdaExecutionRoleArn
```

## Changes Made

### File: `serverless/cloudformation/api-gateway-template.yaml`

**MessageHandlerFunction (line 76):**
```diff
  Runtime: python3.11
+ Handler: index.lambda_handler
  Role: !Ref LambdaExecutionRoleArn
```

**OmpAgentHandlerFunction (line 161):**
```diff
  Runtime: python3.11
+ Handler: index.lambda_handler
  Role: !Ref LambdaExecutionRoleArn
```

## Why This Works

When using CloudFormation's `ZipFile` property with inline Python code:
- The code is automatically saved to a file named `index.py`
- The handler must point to `index.lambda_handler`
- Lambda uses this to find the entry point function

Example:
```python
# This is in index.py (created by CloudFormation)
def lambda_handler(event, context):
    # Handler code here
    return response

# Handler parameter tells Lambda: "Run lambda_handler from index.py"
Handler: index.lambda_handler
```

## Next Steps

1. **GitHub Actions** will automatically run the updated workflow
   - Check: https://github.com/ozbillwang/discord-fleet/actions

2. **Expected Result:**
   - ✅ DynamoDB stack check passes
   - ✅ Lambda layer published
   - ✅ MessageHandlerFunction created ✅
   - ✅ OmpAgentHandlerFunction created ✅
   - ✅ API Gateway deployed ✅
   - ✅ Webhook URL extracted ✅

3. **Copy webhook URL** from workflow output

4. **Configure Discord:**
   - Add webhook URL to Guild Manager bot
   - Add webhook URL to Bot User bot

## Verification

After deployment, verify Lambda functions:

```bash
# List Lambda functions
aws lambda list-functions --region us-east-1 \
  --query 'Functions[?starts_with(FunctionName, `discord-fleet`)]' \
  --output table

# Check function details
aws lambda get-function --function-name discord-fleet-message-handler --region us-east-1
```

Should show:
- ✅ Runtime: python3.11
- ✅ Handler: index.lambda_handler
- ✅ Layers: discord-fleet-dependencies

---

**Status: ✅ Fixed & Pushed**

Workflow should now deploy successfully!

**Commit:** `8db999a` - fix: add Handler parameter to Lambda functions in CloudFormation
