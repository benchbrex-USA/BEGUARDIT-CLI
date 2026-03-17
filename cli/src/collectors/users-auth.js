// Cyber collector: users-auth (§7.2)
// Collects: user accounts, sudo config, SSH key inventory, password policy
// Profiles: standard, deep
import { existsSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import BaseCollector from './base.js';

export default class UsersAuthCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'users-auth';
    this.category = 'cyber';
    this.platforms = ['linux', 'darwin'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];
    const platform = process.platform;

    // ── User accounts ───────────────────────────────────────────────
    const passwdRaw = this.exec('cat /etc/passwd 2>/dev/null');
    if (passwdRaw) {
      const users = passwdRaw.split('\n').filter(Boolean).map((line) => {
        const [name, , uid, gid, gecos, home, shell] = line.split(':');
        return { name, uid: parseInt(uid, 10), gid: parseInt(gid, 10), gecos, home, shell };
      });

      const humanUsers = users.filter((u) => u.uid >= 500 || u.uid === 0);
      const loginShells = users.filter((u) =>
        u.shell && !u.shell.includes('nologin') && !u.shell.includes('false'),
      );

      evidence.push(this.evidence('user_accounts', {
        total: users.length,
        human_users: humanUsers.length,
        login_capable: loginShells.length,
        root_uid_count: users.filter((u) => u.uid === 0).length,
        users: humanUsers.map((u) => ({ name: u.name, uid: u.uid, shell: u.shell, home: u.home })),
      }));

      for (const u of humanUsers) {
        assets.push(this.asset('user_account', u.name, { uid: u.uid, shell: u.shell }));
      }
    }

    // ── Sudo configuration ──────────────────────────────────────────
    const sudoers = this.exec('cat /etc/sudoers 2>/dev/null');
    if (sudoers) {
      const rules = sudoers.split('\n')
        .filter((l) => l.trim() && !l.startsWith('#') && !l.startsWith('Defaults'));
      const nopasswd = rules.filter((r) => r.includes('NOPASSWD'));

      evidence.push(this.evidence('sudo_config', {
        rule_count: rules.length,
        nopasswd_rules: nopasswd.length,
        nopasswd_entries: nopasswd.map((r) => r.trim()),
      }));
    }

    // ── SSH keys inventory ──────────────────────────────────────────
    const sshDir = join(process.env.HOME || '/root', '.ssh');
    const sshKeys = [];
    if (existsSync(sshDir)) {
      try {
        const files = readdirSync(sshDir);
        for (const file of files) {
          const fullPath = join(sshDir, file);
          try {
            const stat = statSync(fullPath);
            if (stat.isFile()) {
              const isPrivate = !file.endsWith('.pub') && !file.startsWith('known_hosts') &&
                !file.startsWith('config') && !file.startsWith('authorized_keys');
              const mode = (stat.mode & 0o777).toString(8);
              sshKeys.push({
                file,
                is_private_key: isPrivate,
                permissions: mode,
                overly_permissive: isPrivate && parseInt(mode, 8) > 0o600,
                size: stat.size,
              });
            }
          } catch { /* stat failed */ }
        }
      } catch { /* readdir failed */ }
    }
    evidence.push(this.evidence('ssh_keys', {
      keys: sshKeys,
      count: sshKeys.length,
      overly_permissive_count: sshKeys.filter((k) => k.overly_permissive).length,
    }));

    // ── Authorized keys ─────────────────────────────────────────────
    const authKeysPath = join(sshDir, 'authorized_keys');
    if (existsSync(authKeysPath)) {
      const authKeys = this.exec(`wc -l < "${authKeysPath}" 2>/dev/null`);
      evidence.push(this.evidence('authorized_keys', {
        path: authKeysPath,
        key_count: parseInt(authKeys, 10) || 0,
      }));
    }

    // ── Deep profile: password aging policy ─────────────────────────
    if (context.profile === 'deep' && platform === 'linux') {
      const loginDefs = this.exec('cat /etc/login.defs 2>/dev/null');
      if (loginDefs) {
        const extract = (key) => {
          const match = loginDefs.match(new RegExp(`^${key}\\s+(\\S+)`, 'm'));
          return match ? match[1] : null;
        };
        evidence.push(this.evidence('password_policy', {
          pass_max_days: extract('PASS_MAX_DAYS'),
          pass_min_days: extract('PASS_MIN_DAYS'),
          pass_min_len: extract('PASS_MIN_LEN'),
          pass_warn_age: extract('PASS_WARN_AGE'),
          encrypt_method: extract('ENCRYPT_METHOD'),
        }));
      }
    }

    return { evidence, assets };
  }
}
