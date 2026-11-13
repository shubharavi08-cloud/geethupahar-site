#!/usr/bin/env bash
# One-time installer: makes the server pull updates from GitHub every 5 minutes.
# Keeps .env and data/ untouched (they are git-ignored).
set -e
APP=/root/songsite
REPO=https://github.com/shubharavi08-cloud/geethupahar-site.git
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq git >/dev/null
cd "$APP"
[ -d .git ] || { git init -q -b main; git remote add origin "$REPO"; }
git fetch -q origin main
git reset -q --hard origin/main
cat > /root/autoupdate.sh <<'EOF'
#!/usr/bin/env bash
cd /root/songsite || exit 1
git fetch -q origin main || exit 0
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  git reset -q --hard origin/main
  docker compose up -d --build >> /root/autoupdate.log 2>&1
  echo "$(date) updated to $(git rev-parse --short HEAD)" >> /root/autoupdate.log
fi
EOF
chmod +x /root/autoupdate.sh
echo '*/5 * * * * root /root/autoupdate.sh' > /etc/cron.d/geethupahar-autoupdate
docker compose up -d --build
echo "AUTO-UPDATE READY. Site updates itself from GitHub every 5 minutes."
