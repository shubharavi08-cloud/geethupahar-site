#!/usr/bin/env bash
# One-time (and re-runnable) server setup for Ubuntu 24.04. Run as root from inside this folder:  bash setup.sh
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
[ "$(id -u)" = 0 ] || { echo "Run as root."; exit 1; }
export DEBIAN_FRONTEND=noninteractive

echo "== 1/6 System packages"
apt-get update -qq
apt-get install -y -qq ca-certificates curl ufw unzip openssl cron

echo "== 2/6 Docker"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  apt-get install -y -qq docker.io docker-compose-v2 || { curl -fsSL https://get.docker.com | sh; }
fi
systemctl enable --now docker

echo "== 3/6 Swap (safety for builds and renders)"
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== 4/6 Firewall (only SSH, web and secure web)"
ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "== 5/6 Settings file (.env)"
NEWPW=""
if [ ! -f .env ]; then
  NEWPW="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)"
  cat > .env <<ENV
DOMAIN=$(python3 -c "import json;print(json.load(open('config.json'))['domain'])" 2>/dev/null || echo geethupahar.com)
ADMIN_PASSWORD=$NEWPW
SESSION_SECRET=$(openssl rand -hex 32)
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
ENV
  chmod 600 .env
fi

echo "== 6/6 Start the site + daily backup"
mkdir -p data /root/backups
docker compose up -d --build
cat > /etc/cron.d/geethupahar-backup <<CRON
30 3 * * * root tar -czf /root/backups/data-\$(date +\%F).tgz -C $(pwd) data && find /root/backups -name 'data-*.tgz' -mtime +7 -delete
CRON
sleep 8
docker compose ps
echo
echo "=============================================================="
echo " Site containers started. Check:  https://$(grep ^DOMAIN= .env | cut -d= -f2)"
if [ -n "$NEWPW" ]; then
  echo " ADMIN PASSWORD (save it now, shown only once): $NEWPW"
  echo " Admin page: https://$(grep ^DOMAIN= .env | cut -d= -f2)/admin.html"
else
  echo " Existing .env kept (admin password unchanged)."
fi
echo "=============================================================="
