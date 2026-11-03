#!/bin/bash
# ==============================================================================
# Aguatech IndiaMART Autoclick Pro - 24/7 Oracle VM Deployment Script
# Installs: Swap (2GB), Google Chrome, Xvfb (Virtual Display), x11vnc, noVNC
# Access: Web browser at http://<VM_IP>:6080/vnc.html
# ==============================================================================

set -e

echo "=== [1/6] Disabling any stuck Tailscale exit node routing ==="
sudo tailscale set --exit-node="" 2>/dev/null || true

echo "=== [2/6] Configuring 2GB Swap Memory for Chrome stability ==="
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swapfile..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap enabled successfully."
else
    echo "Swapfile already exists."
fi

echo "=== [3/6] Opening OS Firewall for Web Remote Screen (Port 6080) ==="
if command -v firewall-cmd &>/dev/null; then
    sudo firewall-cmd --permanent --add-port=22/tcp 2>/dev/null || true
    sudo firewall-cmd --permanent --add-port=6080/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
fi
sudo iptables -I INPUT -p tcp --dport 6080 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || true

echo "=== [4/6] Installing Dependencies (Xvfb, x11vnc, Git, Chrome) ==="
sudo yum install -y epel-release 2>/dev/null || sudo dnf install -y oracle-epel-release-el8 2>/dev/null || true
sudo yum install -y wget xorg-x11-server-Xvfb x11vnc git python3-numpy 2>/dev/null || true

# Install Official Google Chrome
if ! command -v google-chrome &>/dev/null; then
    echo "Downloading and installing Google Chrome for Linux..."
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm -O /tmp/chrome.rpm
    sudo yum localinstall -y /tmp/chrome.rpm || sudo dnf install -y /tmp/chrome.rpm
    rm -f /tmp/chrome.rpm
fi
echo "Google Chrome is installed: $(google-chrome --version)"

# Install noVNC (HTML5 browser remote screen)
if [ ! -d /opt/novnc ]; then
    echo "Installing noVNC web viewer..."
    sudo git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc
    sudo git clone --depth 1 https://github.com/novnc/websockify /opt/novnc/utils/websockify
fi

echo "=== [5/6] Syncing Latest Extension Code ==="
cd /home/opc
if [ ! -d "aguatech-indiamart-autobuy" ]; then
    git clone https://github.com/yogeshkp85-bit/aguatech-indiamart-autobuy.git
else
    cd aguatech-indiamart-autobuy
    git pull origin main || true
    cd /home/opc
fi

# Stop and disable old python bot service if present
sudo systemctl stop aguatech-bot.service 2>/dev/null || true
sudo systemctl disable aguatech-bot.service 2>/dev/null || true

echo "=== [6/6] Creating 24/7 Autostart Services ==="

# Launcher script for Xvfb, noVNC and Chrome
cat << 'EOF' > /home/opc/run_browser.sh
#!/bin/bash
export DISPLAY=:99
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

# 1. Start Virtual Screen
Xvfb :99 -screen 0 1920x1080x24 -ac &
XVFB_PID=$!
sleep 2

# 2. Start VNC screen capture
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -quiet &
X11VNC_PID=$!
sleep 1

# 3. Start noVNC Web Server on port 6080
/opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &
NOVNC_PID=$!
sleep 1

# 4. Launch Google Chrome with IndiaMART Extension
google-chrome \
    --no-first-run \
    --no-default-browser-check \
    --disable-gpu \
    --window-size=1920,1080 \
    --window-position=0,0 \
    --user-data-dir=/home/opc/indiamart-chrome-profile \
    --load-extension="/home/opc/aguatech-indiamart-autobuy/Autobuy lead extension" \
    "https://seller.indiamart.com/bltxn/?pref=relevant"
EOF

chmod +x /home/opc/run_browser.sh

# Create Systemd 24/7 service
sudo bash -c 'cat << "EOF" > /etc/systemd/system/indiamart-extension.service
[Unit]
Description=IndiaMART Chrome Extension 24/7 Service
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc
ExecStart=/home/opc/run_browser.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable indiamart-extension.service
sudo systemctl restart indiamart-extension.service

echo ""
echo "=========================================================================="
echo "🎉 SUCCESS: Chrome & Extension are now running 24/7 in the background!"
echo "=========================================================================="
echo "Open your web browser on your laptop or phone to view Chrome:"
echo "👉 http://$(curl -s ifconfig.me):6080/vnc.html"
echo "or via Tailscale: http://100.103.78.21:6080/vnc.html"
echo "=========================================================================="
