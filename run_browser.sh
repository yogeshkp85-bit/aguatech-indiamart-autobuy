#!/bin/bash
export DISPLAY=:99
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

# Kill old lingering processes
pkill -f "python3 /home/opc/failover_proxy.py" 2>/dev/null || true
pkill -f "python3 /home/opc/web_dashboard.py" 2>/dev/null || true
pkill -f "novnc_proxy" 2>/dev/null || true
pkill -f "x11vnc" 2>/dev/null || true
pkill -f "Xvfb" 2>/dev/null || true
pkill -f "google-chrome" 2>/dev/null || true
sleep 1

# 1. Start Auto-Failover Proxy Dispatcher on 127.0.0.1:8888
python3 /home/opc/failover_proxy.py > /home/opc/failover_proxy.log 2>&1 &
echo "[SYSTEM] Failover Proxy started"
sleep 1

# 2. Start Web Management Dashboard on port 8080
python3 /home/opc/web_dashboard.py > /home/opc/web_dashboard.log 2>&1 &
echo "[SYSTEM] Web Dashboard started on http://100.103.78.21:8080"
sleep 1

# 3. Start Virtual Screen
Xvfb :99 -screen 0 1920x1080x24 -ac &
XVFB_PID=$!
sleep 2

# 4. Start VNC screen capture
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -quiet &
X11VNC_PID=$!
sleep 1

# 5. Start noVNC Web Server on port 6080
/opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &
NOVNC_PID=$!
sleep 1

# 6. Launch Google Chrome with Failover Proxy & Latest Extension
echo "[SYSTEM] Launching Google Chrome..."
google-chrome \
    --no-first-run \
    --no-default-browser-check \
    --disable-gpu \
    --window-size=1920,1080 \
    --window-position=0,0 \
    --proxy-server="http://127.0.0.1:8888" \
    --user-data-dir=/home/opc/indiamart-chrome-profile \
    --load-extension="/home/opc/Indiamartgoogleextension" \
    "https://seller.indiamart.com/bltxn/?pref=relevant"
