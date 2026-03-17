// Cyber collector: network (§7.2)
// Collects: open ports, listening services, interfaces, firewall rules, DNS config
// Profiles: standard, deep
import os from 'node:os';
import BaseCollector from './base.js';

export default class NetworkCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'network';
    this.category = 'cyber';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];
    const platform = process.platform;

    // ── Listening ports ─────────────────────────────────────────────
    const listeners = [];
    if (platform === 'linux') {
      const raw = this.exec('ss -tlnp 2>/dev/null') || this.exec('netstat -tlnp 2>/dev/null');
      if (raw) listeners.push(...this._parseLinuxListeners(raw));
    } else if (platform === 'darwin') {
      const raw = this.exec('lsof -iTCP -sTCP:LISTEN -nP 2>/dev/null');
      if (raw) listeners.push(...this._parseDarwinListeners(raw));
    } else if (platform === 'win32') {
      const raw = this.exec('netstat -ano -p TCP 2>nul');
      if (raw) listeners.push(...this._parseWindowsListeners(raw));
    }
    evidence.push(this.evidence('listening_ports', { ports: listeners, count: listeners.length }));

    for (const l of listeners) {
      assets.push(this.asset('network_service', `${l.address}:${l.port}`, { process: l.process, protocol: 'tcp' }));
    }

    // ── Network interfaces ──────────────────────────────────────────
    const ifaces = [];
    for (const [name, addrs] of Object.entries(os.networkInterfaces())) {
      for (const addr of addrs) {
        ifaces.push({ name, address: addr.address, family: addr.family, internal: addr.internal, mac: addr.mac });
      }
    }
    evidence.push(this.evidence('network_interfaces', { interfaces: ifaces }));

    // ── DNS configuration ───────────────────────────────────────────
    if (platform === 'linux') {
      const resolv = this.exec('cat /etc/resolv.conf 2>/dev/null');
      if (resolv) {
        const nameservers = resolv.split('\n').filter((l) => l.startsWith('nameserver')).map((l) => l.split(/\s+/)[1]);
        evidence.push(this.evidence('dns_config', { nameservers }));
      }
    } else if (platform === 'darwin') {
      const scutil = this.exec('scutil --dns 2>/dev/null');
      if (scutil) {
        const nameservers = [...scutil.matchAll(/nameserver\[\d+\]\s*:\s*(\S+)/g)].map((m) => m[1]);
        evidence.push(this.evidence('dns_config', { nameservers: [...new Set(nameservers)] }));
      }
    }

    // ── Firewall status ─────────────────────────────────────────────
    if (platform === 'linux') {
      const iptables = this.exec('iptables -L -n 2>/dev/null');
      const nftables = this.exec('nft list ruleset 2>/dev/null');
      const ufw = this.exec('ufw status 2>/dev/null');
      evidence.push(this.evidence('firewall', {
        iptables_rules: iptables ? iptables.split('\n').length : 0,
        nftables_available: nftables !== null,
        ufw_status: ufw?.includes('active') ? 'active' : ufw?.includes('inactive') ? 'inactive' : 'unknown',
      }));
    } else if (platform === 'darwin') {
      const pf = this.exec('/sbin/pfctl -s info 2>/dev/null');
      const alf = this.exec('defaults read /Library/Preferences/com.apple.alf globalstate 2>/dev/null');
      evidence.push(this.evidence('firewall', {
        pf_enabled: pf?.includes('Enabled') || false,
        application_firewall: alf === '1' || alf === '2' ? 'enabled' : 'disabled',
      }));
    }

    // ── Deep profile: routing table ─────────────────────────────────
    if (context.profile === 'deep') {
      const routes = this.exec(platform === 'win32' ? 'route print' : 'netstat -rn 2>/dev/null');
      if (routes) evidence.push(this.evidence('routing_table', { raw: routes }));
    }

    return { evidence, assets };
  }

  _parseLinuxListeners(raw) {
    const lines = raw.split('\n').slice(1); // skip header
    return lines.filter((l) => l.trim()).map((line) => {
      const parts = line.split(/\s+/);
      const local = parts[3] || '';
      const lastColon = local.lastIndexOf(':');
      return {
        address: local.slice(0, lastColon) || '0.0.0.0',
        port: parseInt(local.slice(lastColon + 1), 10) || 0,
        process: parts[6] || 'unknown',
      };
    }).filter((l) => l.port > 0);
  }

  _parseDarwinListeners(raw) {
    const lines = raw.split('\n').slice(1);
    return lines.filter((l) => l.trim()).map((line) => {
      const parts = line.split(/\s+/);
      const name = parts[0] || 'unknown';
      const addr = parts[8] || '';
      const lastColon = addr.lastIndexOf(':');
      return {
        address: addr.slice(0, lastColon) || '*',
        port: parseInt(addr.slice(lastColon + 1), 10) || 0,
        process: name,
      };
    }).filter((l) => l.port > 0);
  }

  _parseWindowsListeners(raw) {
    const lines = raw.split('\n').filter((l) => l.includes('LISTENING'));
    return lines.map((line) => {
      const parts = line.trim().split(/\s+/);
      const local = parts[1] || '';
      const lastColon = local.lastIndexOf(':');
      return {
        address: local.slice(0, lastColon) || '0.0.0.0',
        port: parseInt(local.slice(lastColon + 1), 10) || 0,
        process: parts[4] || 'unknown',
      };
    }).filter((l) => l.port > 0);
  }
}
