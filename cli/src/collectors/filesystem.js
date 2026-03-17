// Cyber collector: filesystem (§7.2)
// Collects: file permissions, SUID/SGID binaries, world-writable paths, tmp dirs
// Profiles: deep (intensive scan)
import { existsSync, statSync } from 'node:fs';
import BaseCollector from './base.js';

export default class FilesystemCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'filesystem';
    this.category = 'cyber';
    this.platforms = ['linux', 'darwin'];
    this.profiles = ['deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];

    // ── SUID/SGID binaries ──────────────────────────────────────────
    const suidRaw = this.exec('find / -perm -4000 -type f 2>/dev/null | head -200');
    const sgidRaw = this.exec('find / -perm -2000 -type f 2>/dev/null | head -200');

    const suidBinaries = suidRaw ? suidRaw.split('\n').filter(Boolean) : [];
    const sgidBinaries = sgidRaw ? sgidRaw.split('\n').filter(Boolean) : [];

    evidence.push(this.evidence('suid_binaries', {
      paths: suidBinaries,
      count: suidBinaries.length,
    }));
    evidence.push(this.evidence('sgid_binaries', {
      paths: sgidBinaries,
      count: sgidBinaries.length,
    }));

    for (const path of suidBinaries) {
      assets.push(this.asset('suid_binary', path, { type: 'suid' }));
    }

    // ── World-writable directories ──────────────────────────────────
    const worldWritable = this.exec(
      'find / -type d -perm -0002 ! -perm -1000 2>/dev/null | head -100',
    );
    const wwDirs = worldWritable ? worldWritable.split('\n').filter(Boolean) : [];
    evidence.push(this.evidence('world_writable_dirs', {
      paths: wwDirs,
      count: wwDirs.length,
    }));

    // ── Temp directory analysis ─────────────────────────────────────
    const tmpDirs = ['/tmp', '/var/tmp', '/dev/shm'];
    const tmpInfo = [];
    for (const dir of tmpDirs) {
      if (existsSync(dir)) {
        try {
          const stat = statSync(dir);
          const mode = (stat.mode & 0o777).toString(8);
          const stickyBit = (stat.mode & 0o1000) !== 0;
          const fileCount = this.exec(`ls -1 "${dir}" 2>/dev/null | wc -l`);
          tmpInfo.push({
            path: dir,
            permissions: mode,
            sticky_bit: stickyBit,
            file_count: parseInt(fileCount, 10) || 0,
          });
        } catch { /* stat failed */ }
      }
    }
    evidence.push(this.evidence('tmp_directories', { directories: tmpInfo }));

    // ── Sensitive file permissions ───────────────────────────────────
    const sensitiveFiles = [
      '/etc/shadow', '/etc/gshadow', '/etc/passwd', '/etc/group',
      '/etc/sudoers', '/etc/ssh/sshd_config',
    ];
    const filePerms = [];
    for (const filePath of sensitiveFiles) {
      if (existsSync(filePath)) {
        try {
          const stat = statSync(filePath);
          const mode = (stat.mode & 0o777).toString(8);
          filePerms.push({
            path: filePath,
            permissions: mode,
            owner_uid: stat.uid,
            group_gid: stat.gid,
          });
        } catch { /* stat failed */ }
      }
    }
    evidence.push(this.evidence('sensitive_file_permissions', { files: filePerms }));

    // ── Cron directories ────────────────────────────────────────────
    const cronDirs = ['/etc/cron.d', '/etc/cron.daily', '/etc/cron.hourly', '/etc/cron.weekly', '/etc/cron.monthly'];
    const cronFiles = [];
    for (const dir of cronDirs) {
      const ls = this.exec(`ls -la "${dir}" 2>/dev/null`);
      if (ls) {
        const count = ls.split('\n').filter((l) => !l.startsWith('total') && l.trim()).length - 1;
        cronFiles.push({ directory: dir, file_count: Math.max(count, 0) });
      }
    }
    evidence.push(this.evidence('cron_directories', { directories: cronFiles }));

    return { evidence, assets };
  }
}
