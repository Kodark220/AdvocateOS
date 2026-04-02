#!/usr/bin/env bash
# ───────────────────────────────────────────────────────
#  Oracle Cloud VM Hardening Script for AdvocateOS
#  Run AFTER rebooting the instance from Oracle Console
#  Usage: ssh ubuntu@79.76.62.48 'bash -s' < harden.sh
# ───────────────────────────────────────────────────────
set -euo pipefail

echo "=== 1. Add 1GB swap file ==="
if [ -f /swapfile ]; then
  echo "Swap file already exists, skipping"
else
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "Swap file created and enabled"
fi
free -h

echo ""
echo "=== 2. Tune swap & memory pressure ==="
sudo sysctl vm.swappiness=60
sudo sysctl vm.vfs_cache_pressure=50
echo 'vm.swappiness=60' | sudo tee -a /etc/sysctl.d/99-advocateos.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-advocateos.conf

echo ""
echo "=== 3. Protect advocateos-api from OOM killer ==="
# Find gunicorn master PID and lower its OOM score
GPID=$(pgrep -f 'gunicorn.*dashboard:app' | head -1) || true
if [ -n "$GPID" ]; then
  echo -500 | sudo tee /proc/${GPID}/oom_score_adj
  echo "Set OOM score -500 for gunicorn PID $GPID"
else
  echo "Gunicorn not running yet (will be protected after restart)"
fi

echo ""
echo "=== 4. Harden systemd service ==="
sudo mkdir -p /etc/systemd/system/advocateos-api.service.d
cat <<'OVERRIDE' | sudo tee /etc/systemd/system/advocateos-api.service.d/memory.conf
[Service]
# Auto-restart on failure
Restart=always
RestartSec=5

# Reduce OOM kill priority
OOMScoreAdjust=-500

# Limit memory to prevent runaway processes (800MB of 1GB RAM + 1GB swap)
MemoryMax=800M
MemoryHigh=600M

# Watchdog: restart if unresponsive for 60s
WatchdogSec=60
OVERRIDE
sudo systemctl daemon-reload
echo "Systemd override applied"

echo ""
echo "=== 5. Pull latest code & restart service ==="
cd /home/ubuntu
if [ -d ".git" ]; then
  git pull origin main
  echo "Code updated"
else
  echo "Not a git repo at /home/ubuntu — skipping pull"
fi

sudo systemctl restart advocateos-api
sleep 3
sudo systemctl status advocateos-api --no-pager -l

echo ""
echo "=== 6. Verify API health ==="
sleep 2
curl -s http://localhost:5000/api/health || echo "Health check failed — check logs with: journalctl -u advocateos-api -n 50"

echo ""
echo "=== 7. Schedule daily cleanup cron ==="
CRON_LINE="0 4 * * * /usr/bin/journalctl --vacuum-size=50M && /usr/bin/npm cache clean --force 2>/dev/null"
(crontab -l 2>/dev/null | grep -v 'vacuum-size' ; echo "$CRON_LINE") | crontab -
echo "Cron job added: daily log rotation + npm cache cleanup"

echo ""
echo "=== Done! ==="
echo "Swap:     $(swapon --show --noheadings | awk '{print $3}')"
echo "Memory:   $(free -h | awk '/^Mem:/{print $2}') total, $(free -h | awk '/^Mem:/{print $7}') available"
echo "Service:  $(systemctl is-active advocateos-api)"
