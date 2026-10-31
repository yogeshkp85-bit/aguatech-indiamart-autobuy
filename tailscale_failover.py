"""
Tailscale Auto-Failover Monitor for Aguatech IndiaMART Sniper
Automatically balances outbound IndiaMART requests between:
1. Primary: Office Windows PC (desktop-udgq40p) - active during work hours
2. Secondary: Mobile Gateways (iPhone / Realme Android) - active nights, weekends & holidays
"""

import json
import logging
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Failover] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('TailscaleFailover')

PRIMARY_NAME = 'desktop-udgq40p'
SECONDARY_NAMES = ['yogeshs-iphone-95th', 'realme-16-pro-5g']

current_exit_ip = None

def get_tailscale_status():
    try:
        res = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as e:
        logger.error(f'Failed to get tailscale status: {e}')
        return None

def set_exit_node(target_ip, target_name):
    global current_exit_ip
    if current_exit_ip == target_ip:
        return
    logger.info(f'Switching active exit node -> {target_name} ({target_ip})')
    try:
        subprocess.run(
            ['sudo', 'tailscale', 'set', f'--exit-node={target_ip}', '--exit-node-allow-lan-access=true'],
            check=True,
            capture_output=True
        )
        current_exit_ip = target_ip
        logger.info(f'✅ Successfully active on: {target_name} ({target_ip})')
    except subprocess.CalledProcessError as e:
        logger.error(f'Error switching exit node: {e.stderr.decode()}')

def monitor_loop():
    logger.info('🚀 Tailscale Failover Daemon started. Monitoring PC and Mobile gateways...')
    while True:
        try:
            status = get_tailscale_status()
            if status:
                peers = status.get('Peer', {})
                
                # Check PC
                pc_ready = False
                pc_ip = None
                
                # Check Mobile
                mobile_candidates = []

                for peer in peers.values():
                    hostname = peer.get('HostName', '').lower()
                    dnsname = peer.get('DNSName', '').lower()
                    is_online = peer.get('Online', False)
                    is_exit_opt = peer.get('ExitNodeOption', False)
                    ips = peer.get('TailscaleIPs', [])
                    ip = ips[0] if ips else None

                    if not ip or not is_exit_opt or not is_online:
                        continue

                    if PRIMARY_NAME.lower() in hostname or PRIMARY_NAME.lower() in dnsname:
                        pc_ready = True
                        pc_ip = ip
                    else:
                        for s_name in SECONDARY_NAMES:
                            if s_name.lower() in hostname or s_name.lower() in dnsname:
                                mobile_candidates.append((ip, peer.get('HostName', 'Mobile')))
                                break

                # Decision logic
                if pc_ready and pc_ip:
                    set_exit_node(pc_ip, 'Primary PC (desktop-udgq40p)')
                elif mobile_candidates:
                    m_ip, m_name = mobile_candidates[0]
                    set_exit_node(m_ip, f'Backup Mobile ({m_name})')
                else:
                    found = False
                    for peer in peers.values():
                        if peer.get('ExitNodeOption', False) and peer.get('Online', False):
                            ips = peer.get('TailscaleIPs', [])
                            if ips:
                                set_exit_node(ips[0], peer.get('HostName', 'Fallback'))
                                found = True
                                break
                    if not found and current_exit_ip is not None:
                        logger.warning('No exit node is currently available. Waiting...')

        except Exception as e:
            logger.error(f'Unexpected error in failover loop: {e}')

        time.sleep(5)

if __name__ == '__main__':
    monitor_loop()
