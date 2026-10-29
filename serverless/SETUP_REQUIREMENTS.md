# Setup Requirements Checklist

Before we start deploying agents, please provide/confirm the following:

## 1. AWS Account Setup

### Required Information:
- [ ] AWS Account ID: ___________________
- [ ] AWS Region (default: us-east-1): ___________________
- [ ] AWS Access Key ID: ___________________
- [ ] AWS Secret Access Key: ___________________

### Verification:
- [ ] You have AWS CLI installed locally
- [ ] AWS credentials are configured (or will be provided to agents)
- [ ] Account has sufficient permissions for Lambda, DynamoDB, API Gateway, IAM

**Security Note:** Credentials will be used ONLY for deployment. Agents will use temporary STS tokens.

---

## 2. Discord Setup

### Option A: Create New Server (Recommended for testing)
- [ ] Let agents create a new Discord server
  - Agents will: Create app → Create server → Configure bot
  - You'll get: Server invite link

### Option B: Use Existing Server
- [ ] Existing server name: ___________________
- [ ] Server ID: ___________________
- [ ] Owner ID (your Discord user ID): ___________________
- [ ] Preferred admin channel name: ___________________

### Discord Bot Tokens:
Two separate bot applications needed:

**Bot 1: Guild Manager (Admin Bot)**
- [ ] Will be created by Agent 3 (or provide existing)
- Token will be: `discord-fleet/guild-manager-token`

**Bot 2: Bot User (Member-facing Bot)**
- [ ] Will be created by Agent 3 (or provide existing)
- Token will be: `discord-fleet/bot-user-token`

---

## 3. LLM Configuration

### Claude API:
- [ ] Claude API Key: ___________________
- [ ] Preferred model: ___________________
  - Options: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, etc.
  - Default: `claude-3-5-sonnet-20241022`

### Model Testing:
- [ ] Do you want to test with multiple models (GPT, Gemini)?
  - [ ] Yes - provide additional API keys
  - [ ] No - Claude only for now

---

## 4. Configuration Preferences

### Lambda Configuration:
- [ ] Preferred AWS region: ___________________
- [ ] CloudFormation or Terraform? 
  - [ ] CloudFormation (recommended, simpler)
  - [ ] Terraform (more flexible)
- [ ] DynamoDB on-demand or provisioned?
  - [ ] On-demand (pay per request, default)
  - [ ] Provisioned (predictable cost)

### Performance Targets:
- [ ] Acceptable cold start latency: _____ seconds (default: 3s)
- [ ] Target P95 latency for replies: _____ seconds (default: 3s)
- [ ] Max concurrent users to support: _____ (default: 100)

### Cost Limits:
- [ ] Monthly budget cap: $_____ (default: $50)
- [ ] Should agents monitor costs and alert?
  - [ ] Yes
  - [ ] No

---

## 5. Testing Scope

### What should we test?
- [ ] Unit tests (functions in isolation)
- [ ] Integration tests (components together)
- [ ] Real Discord integration tests (actual bot responding)
- [ ] Load testing (concurrent users)
- [ ] Model switching validation
- [ ] Cost benchmarking

### Test Coverage:
- [ ] Minimum acceptable code coverage: ____% (default: 80%)
- [ ] Should we test failover scenarios?
  - [ ] Yes
  - [ ] No

---

## 6. Deployment Strategy

### Deployment Order:
- [ ] Phase 1: AWS Infrastructure (2 days)
- [ ] Phase 2: Lambda Functions (5 days)
- [ ] Phase 3: Testing (3 days)
- [ ] Phase 4: Production (4 days)

### Monitoring & Alerts:
- [ ] CloudWatch alarms for errors?
  - [ ] Yes (recommended)
  - [ ] No

- [ ] Email/SMS alerts for critical issues?
  - [ ] Yes
  - [ ] No (if yes, provide email: ___________________)

---

## 7. Agent Coordination

### How should agents be organized?

**Option A: Sequential (One after another)**
- Agent 1 completes Phase 1
- Agent 2 starts Phase 2
- Etc.
- **Pros:** Simple, easy to coordinate
- **Cons:** Takes longer
- **Time:** ~14 days

**Option B: Parallel (Multiple agents working simultaneously)**
- Agent 1: Infrastructure provisioning
- Agent 2: Lambda functions development
- Agent 3: Discord integration setup
- Agent 4: Testing framework
- Agent 5: Deployment & monitoring
- **Pros:** Much faster
- **Cons:** More complex coordination
- **Time:** ~7 days

**Recommendation:** Option B (Parallel) for faster completion

### Agent Communication:
- [ ] Use GitHub Issues for coordination?
- [ ] Commit code frequently (daily)?
- [ ] All code reviewed before merge?

---

## 8. Decision Summary

```
Please fill out and confirm:

AWS Account:
- Region: _______________________
- Account ID: _______________________

Discord:
- [ ] Create new server (recommended)
- [ ] Use existing server: _______________________

LLM:
- Claude Key: _______________________
- Preferred Model: _______________________

Deployment:
- Preferred Timeline: [ ] 14 days sequential / [ ] 7 days parallel
- CloudFormation / Terraform: _______________________

Monitoring:
- Cost budget: $_______________________
- Email alerts: _______________________
```

---

## 9. Ready to Start?

Once you've filled this out, here's what happens:

1. **Day 1 Morning:**
   - Agent 1 starts AWS infrastructure provisioning
   - Agent 3 starts Discord setup
   - Agent 4 starts test framework

2. **Day 2:**
   - Agent 2 starts Lambda functions development
   - Agents review Agent 1's infrastructure

3. **Day 3+:**
   - All agents working on their respective tasks
   - Daily progress updates
   - Code reviews as needed

4. **Day 7-14:**
   - Testing and deployment
   - Production validation
   - Documentation

---

**Please provide the required information above, and we can start immediately!** 🚀

Preferred format for submitting:
```
AWS Region: us-east-1
AWS Account ID: 123456789012
AWS Access Key: AKIA...
AWS Secret Key: ...

Discord: Create new server
Claude Key: sk-ant-...
Deployment: Parallel (7 days)
Timeline: ASAP
```

