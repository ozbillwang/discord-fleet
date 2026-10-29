# Discord Fleet Serverless - Implementation Roadmap

## Overview

This document outlines the complete step-by-step implementation plan for converting Discord Fleet from VM-based to AWS Lambda serverless architecture.

## Prerequisites

Before starting, you'll need:

1. **AWS Account** with appropriate permissions
2. **AWS Credentials** (Access Key ID + Secret Access Key)
3. **Discord Server** (new or existing for testing)
4. **Discord Bot Tokens** (will be created during setup)
5. **Claude API Key** (for LLM functionality)

## Implementation Phases

### Phase 1: AWS Infrastructure Setup (Days 1-2)
**Goal:** Create all necessary AWS resources

Tasks:
- [ ] Create IAM roles and policies
- [ ] Create DynamoDB tables (sessions, bindings, agents)
- [ ] Create S3 buckets (logs, configs, artifacts)
- [ ] Create API Gateway
- [ ] Configure CloudWatch logging
- [ ] Set up Secrets Manager for credentials

### Phase 2: Lambda Functions Development (Days 3-7)
**Goal:** Implement all core Lambda functions

Functions to implement:
- [ ] `message_handler` - Route Discord messages
- [ ] `omp_agent_handler` - Process with LLM
- [ ] `guild_manager_handler` - Manage server/channels
- [ ] `interaction_handler` - Handle Discord interactions

### Phase 3: Testing & Validation (Days 8-10)
**Goal:** Ensure everything works correctly

Testing:
- [ ] Unit tests for each Lambda
- [ ] Integration tests with DynamoDB
- [ ] Real Discord integration tests
- [ ] Model switching validation
- [ ] Load testing

### Phase 4: Deployment & Go-Live (Days 11-14)
**Goal:** Deploy to production and verify

Deployment:
- [ ] Deploy CloudFormation stack
- [ ] Configure Discord webhooks
- [ ] Run acceptance tests
- [ ] Monitor metrics
- [ ] Document procedures

---

## Recommended Agent Deployment Strategy

### Agent 1: AWS Infrastructure Provisioning
**Responsibility:** Set up all AWS resources
- Create DynamoDB tables
- Create S3 buckets
- Create IAM roles
- Create API Gateway
- Create Secrets Manager

### Agent 2: Lambda Functions Implementation
**Responsibility:** Write and test Lambda functions
- Implement message_handler
- Implement omp_agent_handler
- Implement guild_manager_handler
- Write unit tests
- Integration tests with DynamoDB

### Agent 3: Discord Integration
**Responsibility:** Connect Discord to Lambda
- Create Discord bot applications
- Register webhooks
- Handle interactions
- Test message routing

### Agent 4: Testing & Validation
**Responsibility:** Comprehensive testing
- Unit test all functions
- Integration tests
- Real Discord conversation tests
- Performance benchmarks
- Security validation

### Agent 5: Deployment & Operations
**Responsibility:** Deploy and monitor
- Deploy to AWS
- Configure monitoring
- Create runbooks
- Handle incidents
- Document procedures

---

## Detailed Task Breakdown

### Phase 1: AWS Infrastructure (Days 1-2)

#### Task 1.1: DynamoDB Tables
Tables needed:
1. `discord-fleet-sessions`
   - PK: thread_id, SK: agent_id
   - Stores conversation history
   - TTL: 30 days

2. `discord-fleet-bindings`
   - PK: channel_id
   - Maps channels to agents
   
3. `discord-fleet-agents`
   - PK: agent_id
   - Stores agent config + system prompt
   
4. `discord-fleet-config`
   - PK: key (e.g., "guild-id", "owner-id")
   - Stores system configuration

#### Task 1.2: S3 Buckets
Buckets needed:
1. `discord-fleet-logs`
   - CloudWatch logs archive
   
2. `discord-fleet-artifacts`
   - Deployment artifacts
   
3. `discord-fleet-generated`
   - Generated images/content

#### Task 1.3: IAM Roles
Roles needed:
1. `LambdaExecutionRole`
   - Permission to call other Lambdas
   - DynamoDB read/write
   - S3 read/write
   - CloudWatch Logs
   - Secrets Manager read

#### Task 1.4: Secrets Manager
Secrets needed:
1. `discord-fleet/guild-manager-token`
   - Guild Manager Discord token
   
2. `discord-fleet/bot-user-token`
   - Bot User Discord token
   
3. `discord-fleet/claude-api-key`
   - Claude API key
   
4. `discord-fleet/webhook-signing-secret`
   - Discord webhook signing secret

#### Task 1.5: API Gateway
Setup:
- Create REST API
- Create resource `/interactions`
- POST method → Lambda integration
- Request/response mapping
- Enable CORS

### Phase 2: Lambda Functions (Days 3-7)

#### Task 2.1: message_handler
```
Input: Discord message event
Process:
  1. Extract message content & channel
  2. Look up channel binding in DynamoDB
  3. Create/get thread session
  4. Invoke omp_agent_handler
Output: Reply (sent to Discord via webhook)
```

#### Task 2.2: omp_agent_handler
```
Input: Message + agent_id + thread_id
Process:
  1. Get agent config from DynamoDB
  2. Get LLM provider (abstraction layer)
  3. Get conversation history from DynamoDB
  4. Call LLM with context
  5. Save to conversation history
Output: Reply text
```

#### Task 2.3: guild_manager_handler
```
Input: Guild Manager command in #admin
Process:
  1. Verify sender is guild owner
  2. Parse command (create topic, delete topic, etc.)
  3. Execute Discord API calls
  4. Update DynamoDB bindings
  5. Log to audit trail
Output: Confirmation message
```

#### Task 2.4: interaction_handler
```
Input: Discord interaction event (message/button/etc)
Process:
  1. Verify Discord signature
  2. Route to appropriate handler
  3. Return response within 3 seconds
Output: Discord interaction response
```

### Phase 3: Testing (Days 8-10)

#### Task 3.1: Unit Tests
Test each function independently:
- message_handler with mock DynamoDB
- omp_agent_handler with mock LLM
- guild_manager_handler with mock Discord API
- interaction_handler with various event types

#### Task 3.2: Integration Tests
Test components together:
- message_handler → omp_agent_handler → DynamoDB
- message_handler → guild_manager_handler → DynamoDB
- Real DynamoDB with test data

#### Task 3.3: Discord Integration Tests
Test with real Discord:
- Create test server
- Send messages to test channel
- Verify bot responds
- Verify threads created
- Verify model switching works

#### Task 3.4: Performance Testing
- Load test with 100 concurrent users
- Measure Lambda cold start
- Measure DynamoDB latency
- Verify scaling behavior

### Phase 4: Deployment (Days 11-14)

#### Task 4.1: CloudFormation Template
Create IaC for all resources:
- DynamoDB tables
- Lambda functions
- IAM roles
- API Gateway
- CloudWatch alarms
- S3 buckets

#### Task 4.2: Deploy to AWS
```bash
aws cloudformation create-stack \
  --stack-name discord-fleet-serverless \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

#### Task 4.3: Configure Discord Webhooks
- Update Discord bot webhook URL to API Gateway
- Verify webhook signature validation
- Test event delivery

#### Task 4.4: Run Acceptance Tests
From `spec/acceptance.md`:
- [ ] A1: Message routing works
- [ ] A2: Agent isolation
- [ ] A3: No host access
- [ ] A4: Model access only via proxy
- [ ] A5: Admin isolation
- [ ] A6: Permission preservation

#### Task 4.5: Production Verification
- Monitor CloudWatch metrics
- Verify no errors in logs
- Test with real users
- Measure performance
- Monitor costs

---

## Resources Needed

### AWS Services
- Lambda (compute)
- DynamoDB (database)
- API Gateway (webhooks)
- CloudWatch (logging)
- S3 (storage)
- IAM (access control)
- Secrets Manager (credentials)
- CloudFormation (IaC)

### External Services
- Discord API (webhooks, interactions)
- Claude API (LLM)

### Credentials Needed
1. AWS Access Key ID
2. AWS Secret Access Key
3. Discord Bot Token (Guild Manager)
4. Discord Bot Token (Bot User)
5. Claude API Key
6. Discord Webhook Signing Secret

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Infrastructure | 2 days | Day 1 | Day 2 |
| Phase 2: Development | 5 days | Day 3 | Day 7 |
| Phase 3: Testing | 3 days | Day 8 | Day 10 |
| Phase 4: Deployment | 4 days | Day 11 | Day 14 |
| **Total** | **14 days** | **Day 1** | **Day 14** |

Actual timeline may vary based on complexity and unexpected issues.

---

## Success Criteria

### Infrastructure Success
- [ ] All DynamoDB tables created and accessible
- [ ] All S3 buckets created
- [ ] IAM roles have correct permissions
- [ ] API Gateway ready to receive webhooks
- [ ] Secrets Manager has all credentials

### Development Success
- [ ] All Lambda functions implemented
- [ ] All functions have unit tests
- [ ] All tests pass (>95% code coverage)
- [ ] No critical security issues
- [ ] Performance meets requirements

### Testing Success
- [ ] All acceptance tests pass (green)
- [ ] Zero message loss
- [ ] Model switching validated
- [ ] Scaling verified
- [ ] Cost estimates accurate

### Deployment Success
- [ ] CloudFormation stack deployed
- [ ] Discord webhooks configured
- [ ] All acceptance tests pass in production
- [ ] CloudWatch metrics healthy
- [ ] Runbooks documented

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Discord API rate limits | Implement queue + backoff |
| DynamoDB hot partitions | Use scatter/gather pattern |
| Lambda cold starts | Provisioned concurrency |
| Concurrent message processing | Proper session locking |
| Cost overruns | CloudWatch alarms + budgets |

---

## Questions to Answer Before Starting

1. **Discord Server:**
   - Use existing server or create new?
   - Do you want to create it before starting, or should agents handle it?

2. **AWS Credentials:**
   - Ready to provide Access Key + Secret?
   - Should credentials be stored in Secrets Manager or environment?

3. **Claude API:**
   - Do you have a Claude API key ready?
   - Any rate limiting preferences?

4. **Testing Scope:**
   - Should we include load testing for 1000+ concurrent users?
   - What's the acceptable P95 latency? (recommend <3 seconds)

5. **Deployment Strategy:**
   - Deploy to us-east-1 or preferred region?
   - Do you want CloudFormation or Terraform?

---

## Next Steps

1. ✅ Answer the questions above
2. ✅ Provide AWS credentials to Agent 1
3. ✅ Create Discord server (or confirm existing one)
4. ✅ Start Phase 1: Infrastructure Provisioning

---

**Ready to begin?** Let's build this! 🚀
