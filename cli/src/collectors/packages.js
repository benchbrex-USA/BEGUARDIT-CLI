// Cyber collector: packages (§7.2)
// Collects: installed packages and versions, package managers detected
// Profiles: standard, deep
import BaseCollector from './base.js';

export default class PackagesCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'packages';
    this.category = 'cyber';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];
    const platform = process.platform;

    // ── System package managers ────────────────────────────────────
    if (platform === 'linux') {
      // dpkg (Debian/Ubuntu)
      const dpkg = this.exec('dpkg-query -W -f \'${Package}\t${Version}\t${Status}\n\' 2>/dev/null');
      if (dpkg) {
        const packages = dpkg.split('\n').filter((l) => l.includes('install ok installed')).map((line) => {
          const [name, version] = line.split('\t');
          return { name, version, manager: 'dpkg' };
        });
        evidence.push(this.evidence('dpkg_packages', { packages, count: packages.length }));
        assets.push(this.asset('package_manager', 'dpkg', { package_count: packages.length }));
      }

      // rpm (RHEL/Fedora)
      const rpm = this.exec('rpm -qa --queryformat "%{NAME}\t%{VERSION}-%{RELEASE}\n" 2>/dev/null');
      if (rpm) {
        const packages = rpm.split('\n').filter(Boolean).map((line) => {
          const [name, version] = line.split('\t');
          return { name, version, manager: 'rpm' };
        });
        evidence.push(this.evidence('rpm_packages', { packages, count: packages.length }));
        assets.push(this.asset('package_manager', 'rpm', { package_count: packages.length }));
      }

      // apk (Alpine)
      const apk = this.exec('apk list --installed 2>/dev/null');
      if (apk) {
        const packages = apk.split('\n').filter(Boolean).map((line) => {
          const match = line.match(/^(\S+)-(\S+)\s/);
          return match ? { name: match[1], version: match[2], manager: 'apk' } : null;
        }).filter(Boolean);
        evidence.push(this.evidence('apk_packages', { packages, count: packages.length }));
        assets.push(this.asset('package_manager', 'apk', { package_count: packages.length }));
      }
    } else if (platform === 'darwin') {
      // Homebrew
      const brew = this.exec('brew list --versions 2>/dev/null');
      if (brew) {
        const packages = brew.split('\n').filter(Boolean).map((line) => {
          const parts = line.split(/\s+/);
          return { name: parts[0], version: parts.slice(1).join(', '), manager: 'homebrew' };
        });
        evidence.push(this.evidence('homebrew_packages', { packages, count: packages.length }));
        assets.push(this.asset('package_manager', 'homebrew', { package_count: packages.length }));
      }

      // Homebrew casks
      if (context.profile === 'deep') {
        const casks = this.exec('brew list --cask --versions 2>/dev/null');
        if (casks) {
          const packages = casks.split('\n').filter(Boolean).map((line) => {
            const parts = line.split(/\s+/);
            return { name: parts[0], version: parts[1] || 'unknown', manager: 'homebrew-cask' };
          });
          evidence.push(this.evidence('homebrew_casks', { packages, count: packages.length }));
        }
      }
    }

    // ── Language-level package managers (all platforms) ────────────
    // pip (Python)
    const pip = this.exec('pip3 list --format=json 2>/dev/null') || this.exec('pip list --format=json 2>/dev/null');
    if (pip) {
      try {
        const packages = JSON.parse(pip).map((p) => ({ name: p.name, version: p.version, manager: 'pip' }));
        evidence.push(this.evidence('pip_packages', { packages, count: packages.length }));
        assets.push(this.asset('package_manager', 'pip', { package_count: packages.length }));
      } catch { /* malformed JSON */ }
    }

    // npm (global)
    const npmGlobal = this.exec('npm list -g --depth=0 --json 2>/dev/null');
    if (npmGlobal) {
      try {
        const parsed = JSON.parse(npmGlobal);
        const deps = parsed.dependencies || {};
        const packages = Object.entries(deps).map(([name, info]) => ({
          name, version: info.version || 'unknown', manager: 'npm-global',
        }));
        evidence.push(this.evidence('npm_global_packages', { packages, count: packages.length }));
        assets.push(this.asset('package_manager', 'npm-global', { package_count: packages.length }));
      } catch { /* malformed JSON */ }
    }

    return { evidence, assets };
  }
}
