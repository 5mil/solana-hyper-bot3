# Deployment Guide

## Solana Hyper-Accumulation Bot v3.0

This guide covers building, pushing, and deploying the bot using Docker and GitHub Actions.

## Prerequisites

- Docker installed locally
- GitHub Personal Access Token with `packages:write` scope
- Access to repository secrets (for live deployment)

## Local Docker Build

### Build Image

```bash
# From repository root
docker build -t hyper-bot3:latest .
```

The Dockerfile:
- Uses `python:3.11-slim` base
- Installs system dependencies (gcc, g++)
- Copies requirements and installs Python packages
- Copies application code (src, config, tools)
- Creates data directory for metrics
- Sets Python path
- Configures health check

### Test Image Locally

```bash
# Run simulation
docker run --rm \
  -v $(pwd)/data:/app/data \
  hyper-bot3:latest \
  python tools/run_simulation.py

# Check health
docker run --rm hyper-bot3:latest python tools/health_check.py

# Run with custom config
docker run --rm \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  hyper-bot3:latest \
  python tools/run_simulation.py
```

## GitHub Container Registry (GHCR)

### Setup GHCR Access

1. Create GitHub Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token with `packages:write` scope
   - Save token securely

2. Add to repository secrets:
   - Go to repository Settings → Secrets → Actions
   - Add secret: `GITHUB_CONTAINER_REGISTRY_PAT`
   - Paste your token

3. Login to GHCR locally:
```bash
echo $GITHUB_CONTAINER_REGISTRY_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

### Push to GHCR

```bash
# Tag image
docker tag hyper-bot3:latest ghcr.io/5mil/solana-hyper-bot3:latest

# Push
docker push ghcr.io/5mil/solana-hyper-bot3:latest

# Tag with version
docker tag hyper-bot3:latest ghcr.io/5mil/solana-hyper-bot3:v3.0.0
docker push ghcr.io/5mil/solana-hyper-bot3:v3.0.0
```

## GitHub Actions Workflows

### 1. Deploy Bot Workflow (`.github/workflows/deploy-bot.yml`)

**Triggers**:
- Push to main/feat branches
- Manual dispatch with mode selection

**Modes**:
- `simulation`: Run extended simulation (execute_trades=false)
- `live-test`: Run with small capital in test mode
- `production`: Run with full capital (requires approval)

**Steps**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Run pytest (unit + integration + simulation tests)
5. Build Docker image
6. Push to GHCR (if PAT present)
7. Run container based on mode
8. Upload simulation reports as artifacts
9. Post PR comment with summary

**Usage**:
```bash
# Trigger via GitHub UI:
# Actions → Deploy Bot → Run workflow
# Select mode: simulation / live-test / production

# Or via gh CLI:
gh workflow run deploy-bot.yml -f mode=simulation
```

### 2. Test Simulation Workflow (`.github/workflows/test-simulation.yml`)

**Triggers**:
- Scheduled (nightly)
- Manual dispatch

**Features**:
- Runs high-fidelity simulation
- Configurable iterations and duration
- Enforces performance thresholds:
  - Win rate ≥ 90%
  - Avg monthly return ≥ 45%
  - Max drawdown ≤ 10%
- Uploads artifacts
- Fails if thresholds not met

**Usage**:
```bash
gh workflow run test-simulation.yml
```

### 3. Emergency Stop Workflow (`.github/workflows/emergency-stop.yml`)

**Triggers**:
- Manual dispatch only

**Actions**:
- Stop running container by name
- Optionally sweep funds to emergency address
- Post incident comment

**Usage**:
```bash
# Via GitHub UI:
# Actions → Emergency Stop → Run workflow
# Input container name and sweep option

# Note: Actual fund sweep requires signed transactions
# and is a placeholder in this scaffold
```

## Deployment Modes

### Simulation Mode

Runs bot with `execute_trades=false` for extended testing:

```bash
# Via workflow
gh workflow run deploy-bot.yml -f mode=simulation

# Via Docker
docker run --rm \
  -e MODE=simulation \
  -v $(pwd)/data:/app/data \
  ghcr.io/5mil/solana-hyper-bot3:latest \
  python tools/run_simulation.py
```

### Live-Test Mode

Runs bot with small capital and real connections (requires secrets):

```bash
# Via workflow (secrets from GitHub)
gh workflow run deploy-bot.yml -f mode=live-test

# Via Docker (secrets from .env)
docker run --rm \
  -e MODE=live \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  ghcr.io/5mil/solana-hyper-bot3:latest \
  python src/live_bot.py
```

**Required secrets**:
- `WALLET_KEYPAIR`: Solana wallet private key
- `RPC_URL`: Solana RPC endpoint (optional, uses default if not set)

### Production Mode

Full production deployment with all capital:

```bash
# Requires manual approval in GitHub Actions
gh workflow run deploy-bot.yml -f mode=production

# Via Docker
docker run -d \
  --name hyper-bot3-prod \
  --restart unless-stopped \
  -e MODE=live \
  --env-file .env.production \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  ghcr.io/5mil/solana-hyper-bot3:latest
```

## Monitoring

### Health Checks

The Docker image includes a health check:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' hyper-bot3-prod

# Manual health check
docker exec hyper-bot3-prod python tools/health_check.py
```

Health check verifies:
- Metrics file exists
- Circuit breaker not triggered
- Bot is responding

### Logs

```bash
# View logs
docker logs -f hyper-bot3-prod

# Save logs to file
docker logs hyper-bot3-prod > logs/bot-$(date +%Y%m%d).log
```

### Metrics

Metrics are persisted to `data/performance_stats.json`:

```bash
# View current metrics
docker exec hyper-bot3-prod cat /app/data/performance_stats.json

# Extract metrics to host
docker cp hyper-bot3-prod:/app/data/performance_stats.json ./data/
```

## Updating Deployment

### Rolling Update

```bash
# Pull latest image
docker pull ghcr.io/5mil/solana-hyper-bot3:latest

# Stop old container
docker stop hyper-bot3-prod
docker rm hyper-bot3-prod

# Start new container
docker run -d \
  --name hyper-bot3-prod \
  --restart unless-stopped \
  -e MODE=live \
  --env-file .env.production \
  -v $(pwd)/data:/app/data \
  ghcr.io/5mil/solana-hyper-bot3:latest
```

### Zero-Downtime Update

```bash
# Start new container with different name
docker run -d \
  --name hyper-bot3-prod-new \
  -e MODE=live \
  --env-file .env.production \
  -v $(pwd)/data:/app/data \
  ghcr.io/5mil/solana-hyper-bot3:latest

# Wait for health check
sleep 30

# If healthy, stop old container
docker stop hyper-bot3-prod
docker rm hyper-bot3-prod

# Rename new container
docker rename hyper-bot3-prod-new hyper-bot3-prod
```

## Security Best Practices

1. **Never commit secrets**: Use environment variables and GitHub secrets
2. **Rotate credentials**: Regularly rotate wallet keys and API tokens
3. **Limit permissions**: Use minimal permissions for wallet keys
4. **Monitor closely**: Set up alerts for unusual activity
5. **Use circuit breaker**: Configure conservative thresholds
6. **Test thoroughly**: Always run simulation before live deployment
7. **Backup data**: Regular backups of metrics and state

## Production Checklist

Before deploying to production:

- [ ] All tests passing in CI
- [ ] Simulation tests meeting thresholds (90% win rate, 45% return, <10% drawdown)
- [ ] Extended simulation completed successfully (1000+ iterations)
- [ ] Docker image built and pushed to GHCR
- [ ] Secrets configured in GitHub repository
- [ ] Circuit breaker thresholds configured appropriately
- [ ] Health check endpoints responding
- [ ] Monitoring and alerting set up
- [ ] Emergency stop procedure tested
- [ ] Backup and recovery plan in place
- [ ] Team notified of deployment

## Troubleshooting

**Issue**: Container exits immediately
- Check logs: `docker logs hyper-bot3-prod`
- Verify secrets are set correctly
- Ensure data volume is writable

**Issue**: Health check failing
- Verify metrics file is being written
- Check circuit breaker status
- Review application logs

**Issue**: No trades executing
- Verify mode is set correctly (simulation vs live)
- Check LogicGate thresholds
- Review min_confidence setting
- Ensure wallet has funds

**Issue**: High loss rate
- Trigger emergency stop immediately
- Review recent trades in metrics
- Check market conditions
- Adjust circuit breaker thresholds

## Support

For issues or questions:
1. Check logs and metrics
2. Review documentation
3. Open GitHub issue
4. Contact team via emergency channels

## Next Steps

After successful deployment:
1. Monitor metrics closely for first 24 hours
2. Review trade logs daily
3. Run weekly simulation tests
4. Update strategies based on performance
5. Scale up gradually after validation
