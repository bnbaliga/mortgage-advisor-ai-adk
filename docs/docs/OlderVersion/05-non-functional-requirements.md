# Non-Functional Requirements

## HomeFirst AI Mortgage Advisor

**Version 1.0 | November 2026**

---

## 1. Performance Requirements

### 1.1 Response Time

| Metric | Target | Measurement |
|--------|--------|-------------|
| Voice-to-voice latency | < 500ms | Time from end of user speech to start of agent response |
| Tool execution time | < 200ms | Time to execute any single tool call |
| WebSocket connection | < 100ms | Time to establish voice connection |
| Page load time | < 2s | Initial web UI load time |
| Health check response | < 50ms | `/health` endpoint response time |

### 1.2 Throughput

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent voice sessions | 100 per instance | Cloud Run auto-scales 0-100 instances |
| Peak capacity | 10,000 concurrent calls | With full auto-scaling |
| Requests per second | 1,000 RPS | Health and metrics endpoints |
| WebSocket messages | 50 msg/sec per session | Audio chunks + tool calls |

### 1.3 Audio Quality

| Metric | Target | Notes |
|--------|--------|-------|
| Input sample rate | 16 kHz | Microphone capture |
| Output sample rate | 24 kHz | Speaker playback |
| Audio codec | PCM 16-bit | Uncompressed for quality |
| Barge-in latency | < 100ms | Interrupt detection |

---

## 2. Availability Requirements

### 2.1 Uptime Targets

| Environment | Target | Downtime Allowed |
|-------------|--------|------------------|
| Production | 99.9% | 8.76 hours/year |
| Staging | 99.5% | 43.8 hours/year |
| Development | 95% | Best effort |

### 2.2 Recovery Objectives

| Metric | Target | Description |
|--------|--------|-------------|
| **RTO** (Recovery Time Objective) | 15 minutes | Maximum time to restore service |
| **RPO** (Recovery Point Objective) | 1 hour | Maximum data loss window |
| **MTTR** (Mean Time To Recovery) | 10 minutes | Average recovery time |
| **MTBF** (Mean Time Between Failures) | 720 hours | Target reliability |

### 2.3 Failover Strategy

| Component | Strategy | Failover Time |
|-----------|----------|---------------|
| Cloud Run instances | Automatic replacement | < 30 seconds |
| Cloud SQL | Multi-zone replication | < 60 seconds |
| Load Balancer | Global anycast | Instant |
| Gemini API | Retry with backoff | 3 retries, 5s max |

---

## 3. Scalability Requirements

### 3.1 Horizontal Scaling

| Metric | Minimum | Maximum | Scaling Trigger |
|--------|---------|---------|-----------------|
| Cloud Run instances | 0 | 100 | CPU > 70% or concurrent requests > 80 |
| Scale-up time | - | 10 seconds | Cold start with container |
| Scale-down time | - | 5 minutes | Gradual cooldown |

### 3.2 Vertical Scaling

| Resource | Allocation | Notes |
|----------|------------|-------|
| vCPU per instance | 1 | Sufficient for voice processing |
| Memory per instance | 1 GB | Includes model context |
| Max request timeout | 300 seconds | Long-running voice sessions |

### 3.3 Data Scaling

| Data Type | Current | 1-Year Target | Storage |
|-----------|---------|---------------|---------|
| Customer records | 10 (seed) | 100,000 | Cloud SQL |
| Loan accounts | 10 (seed) | 500,000 | Cloud SQL |
| Call transcripts | 0 | 1M/month | Cloud Storage |
| Audit logs | 0 | 10M/month | Cloud Logging |

---

## 4. Security Requirements

### 4.1 Authentication & Authorization

| Requirement | Implementation | Standard |
|-------------|----------------|----------|
| API authentication | Google API Key | Required |
| User verification | Two-level (Basic/Strong) | Custom |
| Session management | WebSocket tokens | Stateful |
| Admin access | IAM roles | GCP IAM |

### 4.2 Data Protection

| Requirement | Implementation | Standard |
|-------------|----------------|----------|
| Data in transit | TLS 1.3 | Required |
| Data at rest | AES-256 | Cloud SQL default |
| PII handling | Redaction in logs | CCPA/GDPR |
| Key management | Secret Manager | GCP |

### 4.3 Compliance

| Regulation | Requirement | Implementation |
|------------|-------------|----------------|
| CFPB | Payment authorization | Three-step flow |
| State lending (TX, CA, FL) | HELOC rules | Tool enforcement |
| PCI-DSS | Card data handling | No storage, tokenization |
| SOC 2 | Audit logging | Cloud Logging |

### 4.4 Security Controls

| Control | Target | Implementation |
|---------|--------|----------------|
| Failed login lockout | 3 attempts | Verification lockout |
| Session timeout | 30 minutes | Idle disconnect |
| Rate limiting | 100 req/min per IP | Cloud Armor |
| DDoS protection | Auto-mitigation | Cloud Load Balancer |

---

## 5. Reliability Requirements

### 5.1 Error Handling

| Scenario | Behavior | User Experience |
|----------|----------|-----------------|
| Tool execution failure | Retry once, then fail-closed | "Let me transfer you to an agent" |
| Verification failure (3x) | Account lockout | Transfer to human |
| Unknown state/input | Fail-closed | Route to human agent |
| Network interruption | Reconnect with backoff | "Connection restored" |
| Gemini API timeout | Retry with exponential backoff | Brief pause, then continue |

### 5.2 Graceful Degradation

| Component Failure | Degraded Behavior |
|-------------------|-------------------|
| Database unavailable | Read-only mode from cache |
| Gemini API down | Queue calls, transfer to human |
| Metrics endpoint | Service continues, monitoring gaps |
| Logging service | Buffer locally, retry |

### 5.3 Circuit Breaker Thresholds

| Service | Failure Threshold | Recovery Time |
|---------|-------------------|---------------|
| Gemini API | 5 failures in 30s | 60 seconds |
| Database | 3 failures in 10s | 30 seconds |
| External APIs | 10 failures in 60s | 120 seconds |

---

## 6. Maintainability Requirements

### 6.1 Code Quality

| Metric | Target | Tool |
|--------|--------|------|
| Test coverage | > 50% (current: 53%) | pytest-cov |
| Linting errors | 0 | Ruff |
| Type coverage | > 80% | MyPy |
| Cyclomatic complexity | < 10 per function | Ruff |

### 6.2 Deployment

| Metric | Target | Notes |
|--------|--------|-------|
| Deployment frequency | Daily capable | CI/CD automated |
| Deployment time | < 10 minutes | Build + deploy |
| Rollback time | < 5 minutes | Previous revision |
| Zero-downtime deployment | Required | Rolling updates |

### 6.3 Monitoring & Observability

| Capability | Implementation | Retention |
|------------|----------------|-----------|
| Application logs | Cloud Logging | 30 days |
| Metrics | `/metrics` endpoint + Cloud Monitoring | 90 days |
| Traces | Cloud Trace (future) | 30 days |
| Alerts | Cloud Monitoring | Real-time |

### 6.4 Key Metrics to Monitor

| Metric | Alert Threshold | Severity |
|--------|-----------------|----------|
| Error rate | > 1% | Critical |
| P95 latency | > 1000ms | Warning |
| Instance count | > 80 | Warning |
| Memory usage | > 85% | Warning |
| Failed verifications | > 10/hour | Info |

---

## 7. Usability Requirements

### 7.1 Voice Interaction

| Requirement | Target | Notes |
|-------------|--------|-------|
| Speech recognition accuracy | > 95% | Gemini Live native |
| Barge-in support | Required | Instant interrupt |
| Natural conversation flow | Required | Context preservation |
| Multi-turn conversations | Unlimited | Session-based |

### 7.2 Accessibility

| Requirement | Target | Standard |
|-------------|--------|----------|
| Screen reader support | Required | WCAG 2.1 AA |
| Keyboard navigation | Required | WCAG 2.1 AA |
| Color contrast | 4.5:1 minimum | WCAG 2.1 AA |
| Focus indicators | Visible | WCAG 2.1 AA |

### 7.3 Browser Support

| Browser | Minimum Version | Notes |
|---------|-----------------|-------|
| Chrome | 90+ | Primary target |
| Firefox | 88+ | Supported |
| Safari | 14+ | Supported |
| Edge | 90+ | Supported |
| Mobile Safari | iOS 14+ | Supported |
| Chrome Android | 90+ | Supported |

---

## 8. Compatibility Requirements

### 8.1 API Compatibility

| Requirement | Implementation |
|-------------|----------------|
| Backward compatibility | Semantic versioning |
| API versioning | URL path versioning (future) |
| Deprecation notice | 90 days minimum |

### 8.2 Integration Requirements

| System | Integration Method | SLA |
|--------|-------------------|-----|
| Gemini Live API | Native SDK | Google SLA |
| Cloud SQL | Private VPC | 99.95% |
| Secret Manager | IAM authentication | 99.95% |
| Cloud Storage | Service account | 99.95% |

---

## 9. Capacity Planning

### 9.1 Current Baseline

| Resource | Current | Headroom |
|----------|---------|----------|
| Cloud Run instances | 0-2 | 100 max |
| Database connections | 10 | 100 max |
| Storage | 100 MB | 100 GB allocated |

### 9.2 Growth Projections

| Timeframe | Expected Load | Infrastructure |
|-----------|---------------|----------------|
| Launch | 100 calls/day | 2 instances |
| 3 months | 1,000 calls/day | 10 instances |
| 6 months | 5,000 calls/day | 25 instances |
| 12 months | 20,000 calls/day | 50 instances |

### 9.3 Cost Projections

| Load Level | Monthly Cost | Notes |
|------------|--------------|-------|
| Development | $50 | Minimal usage |
| Launch | $500 | 100 calls/day |
| Growth | $2,500 | 1,000 calls/day |
| Scale | $10,000 | 10,000 calls/day |

---

## 10. Disaster Recovery

### 10.1 Backup Strategy

| Data Type | Frequency | Retention | Location |
|-----------|-----------|-----------|----------|
| Database | Daily | 30 days | Cross-region |
| Configuration | On change | 90 days | Git + Secret Manager |
| Audit logs | Continuous | 1 year | Cloud Logging |
| Call recordings | N/A | Not stored | Privacy |

### 10.2 Recovery Procedures

| Scenario | Procedure | RTO |
|----------|-----------|-----|
| Instance failure | Auto-restart | 30 seconds |
| Region failure | Manual failover | 15 minutes |
| Data corruption | Restore from backup | 1 hour |
| Security breach | Incident response | 4 hours |

### 10.3 Business Continuity

| Scenario | Mitigation |
|----------|------------|
| Primary region down | Failover to secondary region |
| Gemini API outage | Queue and transfer to human |
| Database corruption | Point-in-time recovery |
| Security incident | Isolate, investigate, restore |

---

## Appendix: SLA Summary

| Service Level | Target | Measurement Period |
|---------------|--------|-------------------|
| Availability | 99.9% | Monthly |
| Response time (P95) | < 500ms | Daily |
| Error rate | < 0.1% | Daily |
| Successful calls | > 95% | Weekly |

---

**Document Version:** 1.0
**Last Updated:** November 2026
**Owner:** Engineering Team
