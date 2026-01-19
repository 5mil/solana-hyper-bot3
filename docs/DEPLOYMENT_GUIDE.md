# Deployment Guide

## Docker Build and Deployment

### Prerequisites

1. **Docker installed** (20.10+)
2. **GitHub Container Registry access** (for pushing images)
3. **GitHub PAT** with `packages:write` scope (stored as `GITHUB_CONTAINER_REGISTRY_PAT`)

### Local Docker Build

Build the image:
```bash
docker build -t solana-hyper-bot3:latest .
```

Run simulation locally:
```bash
docker run --rm \
  -v $(pwd)/data:/app/data \
  solana-hyper-bot3:latest \
  --mode simulation --cycles 20
```

### Pushing to GitHub Container Registry

Authenticate:
```bash
echo $GITHUB_CONTAINER_REGISTRY_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

Tag and push:
```bash
docker tag solana-hyper-bot3:latest ghcr.io/5mil/solana-hyper-bot3:latest
docker push ghcr.io/5mil/solana-hyper-bot3:latest
```

## GitHub Actions Workflows

### 1. deploy-bot.yml

**Trigger**: Push to main, manual dispatch

**Steps**:
1. Checkout code
2. Set up Python 3.11
3. Install dependencies
4. Run pytest (unit + integration tests)
5. Build Docker image
6. Push to GHCR (if PAT present)
7. Run container based on mode:
   - **simulation**: Long-running simulation with `execute_trades=false`
   - **live-test**: Short live test (requires `WALLET_KEYPAIR`)
   - **production**: Full live deployment

**Outputs**:
- Test results
- Simulation performance artifacts (JSON reports)
- PR comments with summary (win rate, return, drawdown, trade count)

**Secrets Required**:
- `GITHUB_CONTAINER_REGISTRY_PAT`: For pushing images
- `WALLET_KEYPAIR`: For live/production modes (Base58 encoded)

### 2. test-simulation.yml

**Trigger**: Scheduled (daily), manual dispatch

**Purpose**: High-fidelity simulation gate before production

**Steps**:
1. Run extended simulation (configurable iterations/time)
2. Analyze results
3. Enforce thresholds:
   - Win rate >= 90%
   - Avg monthly return >= 45%
   - Max drawdown <= 10%
4. Upload performance artifacts
5. Fail if thresholds not met

**Usage**:
```bash
# Manual dispatch via GitHub UI
# Set inputs: iterations=1000, delay_sec=0.5
```

**Outputs**:
- Full simulation report (JSON)
- Performance plots (if enabled)
- Threshold compliance report

### 3. emergency-stop.yml

**Trigger**: Manual dispatch only

**Purpose**: Emergency shutdown and fund sweep

**Inputs**:
- `container_name`: Name of running container
- `sweep_funds`: Boolean to trigger fund sweep
- `emergency_address`: Target address for sweep

**Steps**:
1. Stop running container by name
2. (Optional) Execute sweep transaction to emergency address
3. Post incident comment to tracking issue

**Usage**:
```bash
# Via GitHub UI
# Inputs: container_name="bot-production", sweep_funds=true
```

⚠️ **Warning**: Sweep requires `WALLET_KEYPAIR` and valid `EMERGENCY_SWEEP_ADDRESS`

## Workflow Usage Patterns

### Development Workflow

1. Create feature branch
2. Push changes
3. CI runs tests automatically
4. Review test results
5. Merge to main

### Pre-Production Validation

1. Dispatch `test-simulation.yml` with high iterations (1000+)
2. Review performance artifacts
3. Ensure thresholds met
4. If passed, proceed to production

### Production Deployment

1. Dispatch `deploy-bot.yml` with mode="production"
2. Provide `WALLET_KEYPAIR` secret
3. Monitor health check endpoint
4. Review metrics in `data/performance_stats.json`

### Emergency Procedures

1. Dispatch `emergency-stop.yml`
2. Provide container name
3. Set `sweep_funds=true` if needed
4. Verify fund sweep transaction
5. Investigate incident

## Configuration Management

### Environment Variables

Required for live/production:
- `WALLET_KEYPAIR`: Base58 encoded Solana keypair
- `RPC_URL`: Solana RPC endpoint (default: public mainnet)
- `GITHUB_CONTAINER_REGISTRY_PAT`: For CI image push

Optional:
- `JUPITER_API_KEY`: Jupiter aggregator API key
- `DRIFT_API_KEY`: Drift Protocol API key
- `ALERT_WEBHOOK_URL`: Webhook for alerts

### Secrets Management

**Never commit secrets to repository**

Store secrets in:
1. **GitHub Secrets**: For CI/CD workflows
2. **Environment files**: For local development (add to .gitignore)
3. **Secret managers**: For production (AWS Secrets Manager, HashiCorp Vault)

Example `.env` file (not committed):
```bash
WALLET_KEYPAIR=base58_encoded_keypair_here
RPC_URL=https://api.mainnet-beta.solana.com
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

### Health Checks

Run health check:
```bash
python tools/health_check.py
```

Returns:
- Exit 0: Metrics file exists and valid
- Exit 1: Metrics file missing or invalid

Used by container orchestrators (Kubernetes, Docker Compose) for liveness probes.

## Monitoring

### Metrics Collection

Metrics written to `data/performance_stats.json`:
- Updated every cycle in live mode
- Updated at end of simulation

### Alerting

Configure alerts based on metrics:
- `return_pct < -5%`: Daily loss limit
- `win_rate < 40%`: Strategy degradation
- `consecutive_losses >= 5`: Circuit breaker

### Logs

Docker logs:
```bash
docker logs -f container_name
```

Application logs written to stdout (captured by Docker).

## Rollback Procedures

### Rollback Docker Image

```bash
# Pull previous version
docker pull ghcr.io/5mil/solana-hyper-bot3:previous-tag

# Stop current
docker stop bot-production

# Start previous
docker run -d --name bot-production \
  --env-file .env \
  ghcr.io/5mil/solana-hyper-bot3:previous-tag \
  --mode live
```

### Rollback Code

```bash
# Revert commit
git revert HEAD

# Push to trigger CI
git push origin main
```

## Security Considerations

1. **Never log wallet keypairs**
2. **Use environment variables for secrets**
3. **Rotate keys regularly**
4. **Monitor for unauthorized access**
5. **Test emergency sweep in testnet**
6. **Use hardware wallet for production funds**
7. **Implement rate limiting**
8. **Enable IP whitelisting for RPC**

## Scaling

### Horizontal Scaling

Run multiple instances with different configs:
```bash
# Conservative bot
docker run -d --name bot-conservative \
  -e MIN_CONFIDENCE=0.85 \
  -e MAX_POSITION_PCT=0.2 \
  bot:latest

# Aggressive bot
docker run -d --name bot-aggressive \
  -e MIN_CONFIDENCE=0.65 \
  -e MAX_POSITION_PCT=0.5 \
  bot:latest
```

### Resource Limits

Set Docker resource constraints:
```bash
docker run -d \
  --memory=512m \
  --cpus=1.0 \
  bot:latest
```

## Troubleshooting

### Container Won't Start
- Check environment variables
- Verify secrets are set
- Review Docker logs
- Check port conflicts

### No Trades Executing
- Verify `execute_trades: true` in simulation
- Check `min_confidence` threshold
- Review LogicGate blocks in metrics
- Verify wallet has funds (live mode)

### High Latency
- Switch to private RPC endpoint
- Increase `max_latency_ms` threshold
- Check network connectivity
- Consider geographic proximity to RPC

### Failed Health Checks
- Ensure metrics file is being written
- Check write permissions on data directory
- Verify bot is running cycles
- Review error logs
