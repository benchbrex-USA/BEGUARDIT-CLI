// Cyber collector: services (§7.2)
// Collects: running services/daemons, startup items, systemd/launchd units
// Profiles: standard, deep
import BaseCollector from './base.js';

export default class ServicesCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'services';
    this.category = 'cyber';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];
    const platform = process.platform;

    if (platform === 'linux') {
      // ── systemd units ────────────────────────────────────────────
      const unitList = this.exec('systemctl list-units --type=service --state=running --no-pager --plain 2>/dev/null');
      const services = [];
      if (unitList) {
        for (const line of unitList.split('\n').slice(1)) {
          const parts = line.trim().split(/\s+/);
          if (parts.length >= 4 && parts[0].endsWith('.service')) {
            services.push({
              name: parts[0],
              load: parts[1],
              active: parts[2],
              sub: parts[3],
              description: parts.slice(4).join(' '),
            });
          }
        }
      }
      evidence.push(this.evidence('systemd_services', { services, count: services.length }));

      // ── enabled-at-boot services ─────────────────────────────────
      if (context.profile === 'deep') {
        const enabled = this.exec('systemctl list-unit-files --type=service --state=enabled --no-pager --plain 2>/dev/null');
        const enabledServices = [];
        if (enabled) {
          for (const line of enabled.split('\n').slice(1)) {
            const parts = line.trim().split(/\s+/);
            if (parts[0]?.endsWith('.service')) {
              enabledServices.push({ name: parts[0], state: parts[1] || 'enabled' });
            }
          }
        }
        evidence.push(this.evidence('boot_services', { services: enabledServices, count: enabledServices.length }));
      }

      for (const svc of services) {
        assets.push(this.asset('service', svc.name, { description: svc.description, active: svc.active }));
      }
    } else if (platform === 'darwin') {
      // ── launchd services ─────────────────────────────────────────
      const launchctlList = this.exec('launchctl list 2>/dev/null');
      const services = [];
      if (launchctlList) {
        for (const line of launchctlList.split('\n').slice(1)) {
          const parts = line.trim().split(/\t/);
          if (parts.length >= 3) {
            services.push({
              pid: parts[0] === '-' ? null : parseInt(parts[0], 10),
              status: parseInt(parts[1], 10),
              label: parts[2],
            });
          }
        }
      }
      evidence.push(this.evidence('launchd_services', { services, count: services.length }));

      // Running services only
      const running = services.filter((s) => s.pid !== null);
      for (const svc of running) {
        assets.push(this.asset('service', svc.label, { pid: svc.pid }));
      }

      // ── Launch agents/daemons ────────────────────────────────────
      if (context.profile === 'deep') {
        const agentDirs = [
          '/Library/LaunchDaemons',
          '/Library/LaunchAgents',
          `${process.env.HOME}/Library/LaunchAgents`,
        ];
        const plists = [];
        for (const dir of agentDirs) {
          const ls = this.exec(`ls "${dir}" 2>/dev/null`);
          if (ls) {
            for (const file of ls.split('\n').filter((f) => f.endsWith('.plist'))) {
              plists.push({ directory: dir, file });
            }
          }
        }
        evidence.push(this.evidence('launch_plists', { plists, count: plists.length }));
      }
    } else if (platform === 'win32') {
      // ── Windows services ─────────────────────────────────────────
      const raw = this.exec('sc query type= service state= all 2>nul');
      const services = [];
      if (raw) {
        let current = {};
        for (const line of raw.split('\n')) {
          const nameMatch = line.match(/SERVICE_NAME:\s+(.+)/);
          const stateMatch = line.match(/STATE\s+:\s+\d+\s+(\w+)/);
          const displayMatch = line.match(/DISPLAY_NAME:\s+(.+)/);
          if (nameMatch) current = { name: nameMatch[1].trim() };
          if (displayMatch) current.display_name = displayMatch[1].trim();
          if (stateMatch) {
            current.state = stateMatch[1];
            services.push({ ...current });
            current = {};
          }
        }
      }
      evidence.push(this.evidence('windows_services', { services, count: services.length }));

      const running = services.filter((s) => s.state === 'RUNNING');
      for (const svc of running) {
        assets.push(this.asset('service', svc.name, { display_name: svc.display_name }));
      }
    }

    return { evidence, assets };
  }
}
