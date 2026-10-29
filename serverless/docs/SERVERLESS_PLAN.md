# Discord Fleet Serverless Migration - Complete Plan

## Executive Summary

Transform Discord Fleet from a VM-based architecture to a fully serverless AWS Lambda implementation while maintaining all functionality and improving reliability.

## Current Architecture Analysis

### VM Version Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Guild Manager | Hermes Agent (host) | Server management, channel creation, bot binding |
| Discord Bridge | Python + discord.py (container) | Route Discord messages to agents |
| Agents | omp (Bun runtime) | Process messages, maintain conversation memory |
| Model Access | Local proxy gateway | Rate limiting, allowlist enforcement |
| Storage | Filesystem | Session persistence, configuration |
| Security | iptables, rootless docker | Egress filtering, privilege isolation |

## Proposed Lambda Architecture

### Core Changes

| Component | VM Version | Lambda Version | Rationale |
|-----------|-----------|----------------|-----------|
| Guild Manager | Hermes on VM | Lambda function | No need for persistent process |
| Discord Bridge | Container with discord.py | Lambda + Interactions API | No persistent connection needed |
| Agents | omp processes | Lambda + Claude SDK | Stateless per-message processing |
| Storage | Filesystem | DynamoDB | Serverless, auto-scaling |
| Configuration | YAML files | DynamoDB | Centralized, queryable |
| Security | iptables rules | AWS IAM policies | Cloud-native approach |

## Feasibility Assessment

### Requirement Mapping (from spec/topics.md)

| ID | Requirement | VM Solution | Lambda Solution | Feasible? |
|----|-------------|-------------|-----------------|-----------|
| T1 | Channel → Agent binding | bridge.yaml | DynamoDB table | ✅ Yes |
| T2 | No @mention, auto-thread | discord.py events | Interactions API | ✅ Yes |
| T3 | Agent no-tools | omp --no-tools | Lambda restricted SDK | ✅ Yes |
| T4 | Container isolation | rootless docker | AWS IAM isolation | ✅ Yes |
| T5 | Admin channels excluded | config filter | DynamoDB filter | ✅ Yes |
| T6 | Member permissions unchanged | read-only Discord API | read-only Discord API | ✅ Yes |
| T7 | Binding audit trail | hosts/<name>.md | DynamoDB + CloudTrail | ✅ Yes |
| T8 | Separate Guild/Bot apps | two Discord apps | two Discord apps | ✅ Yes |

**Conclusion: 100% feasible** ✅

## Implementation Timeline

### Phase 1: Architecture Design (3-5 days)

- [ ] Define DynamoDB table schemas
- [ ] Design Lambda function signatures
- [ ] Plan IAM policies and VPC configuration
- [ ] Create AWS architecture diagram
- [ ] Document environment variables

### Phase 2: Infrastructure Setup (3-5 days)

- [ ] Create DynamoDB tables (sessions, bindings, agents)
- [ ] Create S3 buckets (configs, logs, generated content)
- [ ] Configure API Gateway for Discord interactions
- [ ] Set up CloudWatch logging and monitoring
- [ ] Create IAM roles and policies

### Phase 3: Core Implementation (7-10 days)

- [ ] Implement LLM abstraction layer (llm_provider.py)
- [ ] Rewrite message_handler Lambda
- [ ] Rewrite omp_agent_handler Lambda
- [ ] Implement guild_manager_handler Lambda
- [ ] Create session management logic
- [ ] Implement binding management

### Phase 4: Testing (3-5 days)

- [ ] Unit tests for all Lambda functions
- [ ] Integration tests with DynamoDB
- [ ] Real Discord integration testing
- [ ] Model switching validation
- [ ] Load testing with multiple concurrent users
- [ ] Security audit (IAM, VPC, secrets)

### Phase 5: Deployment & Migration (2-3 days)

- [ ] Deploy CloudFormation stack
- [ ] Migrate existing data from VM to DynamoDB
- [ ] Point Discord webhooks to Lambda
- [ ] Verify all acceptance tests pass
- [ ] Update documentation
- [ ] Decommission old VM (optional)

**Total Timeline: 3-4 weeks**

## Cost Analysis

### VM Version (Current)
```
Compute:           $5-10/month  (1 small VM, 24/7)
Bandwidth:         ~$0
Storage:           ~$0 (included)
Total:             $5-10/month (fixed cost)

Idle cost:         $5-10/month (always paying)
```

### Lambda Version (Proposed)
```
Lambda executions:  ~$0.20 per million requests
Lambda compute:     ~$0.0000166667 per GB-second
DynamoDB:          ~$1-5/month (pay-per-request)
S3 storage:        ~$0.02 per GB/month
API Gateway:       $0.35 per million requests
Total:             $0-10/month (usage-based)

Idle cost:         $0 (completely free when not in use!)
```

**Monthly savings: 50-100%** depending on usage

## Requirements Met

### Functional Requirements

✅ All Discord interactions identical
✅ Agent isolation maintained
✅ No member permission changes
✅ Admin functions preserved
✅ Session persistence
✅ Configuration management
✅ Audit trail recording

### Non-Functional Requirements

✅ **Scalability:** Auto-scaling to handle traffic spikes
✅ **Reliability:** DynamoDB multi-region durability
✅ **Security:** AWS IAM fine-grained access control
✅ **Maintainability:** Infrastructure as Code (CloudFormation/Terraform)
✅ **Observability:** CloudWatch logs and metrics
✅ **Cost-efficiency:** Pay only for actual usage

### Nice-to-Have Features

✅ **Model flexibility:** Switch LLMs without code changes
✅ **Multi-model support:** Different agents can use different models
✅ **Failover capability:** Automatic fallback if primary model fails
✅ **Cost optimization:** Use cheaper models for simple tasks

## Risk Assessment

### Low Risk ✅
- Switching to HTTP webhook API (Discord supports it)
- DynamoDB for session storage (proven, reliable)
- Lambda function architecture (standard pattern)
- IAM-based security (AWS best practice)

### Medium Risk ⚠️
- Cold start latency (~1-2s on first invocation)
  - Mitigation: Use Provisioned Concurrency if needed (~$0.015/hour)
- Coordinating multi-component deployment
  - Mitigation: Use CloudFormation for atomic deployments

### Minimal Risk ✅
- Guild Manager rewrite (straightforward Lambda function)
- Model adapter removal (clean API via abstraction layer)
- No data loss (DynamoDB handles persistence)

## Rollback Plan

If issues arise:
1. Keep old VM running during transition period
2. Run both systems in parallel for 1-2 weeks
3. Monitor new system logs and metrics
4. Gradual traffic migration (10% → 25% → 50% → 100%)
5. Keep VM until all issues resolved
6. Decommission VM after 30 days of stable Lambda operation

## Success Criteria

### Deployment Success
- [ ] All CloudFormation stacks deploy successfully
- [ ] All Lambda functions respond within 3 seconds
- [ ] DynamoDB tables have <50ms latency
- [ ] API Gateway accepts Discord webhooks

### Functional Success
- [ ] Discord messages processed correctly
- [ ] Agents reply with proper context
- [ ] Session history preserved
- [ ] Channel bindings work as before
- [ ] All spec/acceptance.md tests pass

### Performance Success
- [ ] P95 latency < 3 seconds
- [ ] Zero message loss
- [ ] Zero silent failures
- [ ] CloudWatch shows healthy metrics

### Cost Success
- [ ] Monthly cost < original VM cost
- [ ] No unexpected AWS charges
- [ ] Cost scales linearly with usage

## Acceptance Tests

From `spec/acceptance.md` - must all pass:

```
A1. Message routing
    - Member message in topic channel → thread opens → agent replies

A2. Agent isolation
    - Agent A in channel-1 doesn't share memory with Agent B in channel-2

A3. No host access
    - Agent Lambda can't access host files, tailnet, or internal services

A4. Model access
    - Agent calls Claude API only through allowlist (no direct internet)

A5. Admin isolation
    - #admin messages NOT answered by agents
    - Admin commands work as expected

A6. Permission preservation
    - Members' Discord permissions unchanged
    - No new role grants
```

All tests must pass green before production release.

## Deployment Checklist

- [ ] Architecture reviewed and approved
- [ ] All 5 phases complete
- [ ] Security audit passed
- [ ] Performance tests passed
- [ ] Acceptance tests passed (green)
- [ ] Rollback procedure tested
- [ ] Documentation updated
- [ ] Stakeholders informed
- [ ] Monitoring & alerting configured
- [ ] Runbook created for operations
- [ ] Lambda functions deployed to production
- [ ] DNS/webhooks pointed to Lambda
- [ ] VM shutdown (after verification period)

## Key Success Factors

1. **Comprehensive Testing:** Test each component thoroughly before integration
2. **Gradual Migration:** Run old and new systems in parallel initially
3. **Monitoring:** Real-time visibility into Lambda execution and DynamoDB performance
4. **Documentation:** Keep detailed records of all changes and decisions
5. **Team Communication:** Keep all stakeholders informed of progress

## Conclusion

The proposed serverless architecture is **fully feasible**, provides **cost savings**, **better scalability**, and **improved reliability** while maintaining 100% functional compatibility with the existing VM version.

**Recommendation: Proceed with implementation** ✅
