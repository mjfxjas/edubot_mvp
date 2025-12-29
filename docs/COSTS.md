# Cost Analysis - EduBot MVP

## Overview
EduBot is designed to be cost-effective for educational institutions, with most costs being pay-per-use. This document breaks down the actual costs and optimization strategies.

## Current Monthly Costs (Estimated)

### Free Tier / Minimal Cost
- **Gemini API (Primary)**: FREE
  - 15 requests/minute, 1,500 requests/day
  - Sufficient for small-to-medium school (100-200 students)
  - Auto-fallback to Bedrock when rate limited

### AWS Services (Pay-per-use)

#### Lambda
- **Compute**: ~$0.20/million requests
- **Memory**: 128MB @ $0.0000000021/ms
- **Typical cost**: $5-10/month for 10,000 questions
- **Free tier**: 1M requests + 400,000 GB-seconds/month

#### S3 Storage
- **Storage**: $0.023/GB/month
- **Current usage**: ~500MB (3 textbooks indexed)
- **Cost**: ~$0.01/month
- **Requests**: $0.0004/1000 GET requests
- **Typical cost**: $1-2/month for 50,000 questions

#### Bedrock (Fallback only)
- **Claude 3 Haiku**: $0.25/1M input tokens, $1.25/1M output tokens
- **Average question**: ~5,000 input + 200 output tokens
- **Cost per question**: ~$0.0015
- **Only used when Gemini rate limited**: $5-15/month

#### CloudWatch
- **Logs**: $0.50/GB ingested
- **Metrics**: First 10 custom metrics free
- **Typical cost**: $2-3/month

#### ECR (Docker Registry)
- **Storage**: $0.10/GB/month
- **Current usage**: ~2GB
- **Cost**: $0.20/month

### Total Monthly Cost Breakdown

| Scenario | Students | Questions/Day | Monthly Cost |
|----------|----------|---------------|--------------|
| **Small School** | 50 | 500 | $5-10 |
| **Medium School** | 200 | 2,000 | $15-25 |
| **Large School** | 500 | 5,000 | $40-60 |

## Cost Optimization Strategies

### Implemented
- **Gemini Free Tier First** - Saves ~$0.0015 per question vs Bedrock  
- **Serverless Architecture** - No idle costs, pay only for actual usage  
- **Minimal Lambda Memory** - 128MB sufficient for current workload  
- **S3 Lifecycle Policies** - Old logs auto-deleted after 14 days  

### Recommended (Not Yet Implemented)
- [ ] **ElastiCache/Redis** - Cache popular questions (~$15/month, saves 50%+ on repeated queries)
- [ ] **CloudFront CDN** - Cache frontend assets (~$1/month)
- [ ] **Reserved Capacity** - If usage predictable, save 30-50%
- [ ] **Batch Processing** - Process multiple questions in single Lambda invocation

## Cost Comparison vs Alternatives

| Solution | Monthly Cost | Notes |
|----------|--------------|-------|
| **EduBot (Current)** | $5-60 | Scales with usage |
| **ChatGPT Plus (per student)** | $20/student | $1,000-10,000/month for school |
| **Custom LLM Hosting** | $500-2,000 | GPU instance + maintenance |
| **Traditional Tutoring** | $50-100/hour | Not scalable |

## ROI for Educational Institutions

### Cost Savings
- **vs ChatGPT Plus**: 95%+ savings (curriculum-focused, no per-seat licensing)
- **vs Human Tutors**: 99%+ savings (24/7 availability, instant responses)
- **vs Custom Infrastructure**: 80%+ savings (no DevOps overhead)

### Value Delivered
- 24/7 availability for students
- Curriculum-aligned answers (not generic internet content)
- Scalable to entire student body
- Private data (stays in school's AWS account)

## Monitoring & Alerts

### Cost Controls Implemented
- CloudWatch billing alarms (alert if >$50/month)
- Lambda concurrency limits (prevent runaway costs)
- S3 lifecycle policies (auto-cleanup)
- Gemini rate limiting (prevents excessive Bedrock fallback)

### Recommended Additions
- [ ] AWS Budgets with automatic shutoff
- [ ] Per-student usage quotas
- [ ] Cost allocation tags by department/class

## Scaling Considerations

### Current Capacity
- **Lambda**: Can handle 1,000 concurrent requests
- **Gemini**: 15 req/min = ~21,600 questions/day
- **S3**: Virtually unlimited

### Bottlenecks & Solutions
1. **Gemini Rate Limit** → Add Bedrock capacity or multiple API keys
2. **Lambda Cold Starts** → Provisioned concurrency ($10-20/month)
3. **S3 GET Costs** → Add caching layer (ElastiCache)

## Production Recommendations

For a school deploying this in production:

1. **Start Small**: Use Gemini free tier, monitor for 1 month
2. **Add Caching**: If >1,000 questions/day, add Redis (~$15/month saves $20+)
3. **Set Budgets**: AWS Budget alert at $100/month
4. **Monitor Usage**: Track cost per question, optimize if >$0.01

## Developer Notes

This cost structure demonstrates:
- **Cloud-native thinking**: Pay-per-use vs fixed infrastructure
- **Cost optimization**: Free tier maximization, intelligent fallbacks
- **Production awareness**: Monitoring, alerts, scaling considerations
- **Business value**: Clear ROI vs alternatives

*Last updated: 2025-12-29*
