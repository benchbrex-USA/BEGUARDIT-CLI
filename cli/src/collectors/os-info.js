// Cyber collector: os-info (§7.2)
// Collects: OS version, hostname, kernel, architecture, uptime
// Profiles: quick, standard, deep
import os from 'node:os';
import BaseCollector from './base.js';

export default class OsInfoCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'os-info';
    this.category = 'cyber';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['quick', 'standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];

    const hostname = os.hostname();
    const platform = os.platform();
    const arch = os.arch();
    const release = os.release();
    const type = os.type();
    const uptime = os.uptime();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const cpus = os.cpus();

    const info = {
      hostname,
      platform,
      arch,
      type,
      release,
      uptime_seconds: uptime,
      total_memory_bytes: totalMem,
      free_memory_bytes: freeMem,
      cpu_model: cpus[0]?.model || 'unknown',
      cpu_count: cpus.length,
      node_version: process.version,
    };

    // Platform-specific details
    if (platform === 'linux') {
      const osRelease = this.exec('cat /etc/os-release 2>/dev/null');
      if (osRelease) {
        const parsed = {};
        for (const line of osRelease.split('\n')) {
          const [key, ...rest] = line.split('=');
          if (key && rest.length) parsed[key] = rest.join('=').replace(/^"|"$/g, '');
        }
        info.distro = parsed.PRETTY_NAME || parsed.NAME || 'unknown';
        info.distro_id = parsed.ID;
        info.distro_version = parsed.VERSION_ID;
      }
      info.kernel = this.exec('uname -r');
    } else if (platform === 'darwin') {
      info.macos_version = this.exec('sw_vers -productVersion');
      info.macos_build = this.exec('sw_vers -buildVersion');
      info.kernel = this.exec('uname -r');
      info.sip_status = this.exec('csrutil status 2>/dev/null')?.includes('enabled') ? 'enabled' : 'disabled';
    } else if (platform === 'win32') {
      info.windows_version = this.exec('ver');
    }

    // Network interfaces summary
    const interfaces = os.networkInterfaces();
    info.interface_count = Object.keys(interfaces).length;

    evidence.push(this.evidence('os_info', info));
    assets.push(this.asset('host', hostname, { platform, arch, release }));

    return { evidence, assets };
  }
}
