// Built-in cyber security rules (§7.3)
// Each rule: { id, title, category, score, evaluate(evidence) → finding|null }

export default [
  // ── OS & host ──────────────────────────────────────────────────────
  {
    id: 'CYB-001',
    title: 'Root / UID-0 accounts detected',
    category: 'users-auth',
    score: 7.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'user_accounts');
      if (!e) return null;
      const rootCount = e.data.root_uid_count || 0;
      if (rootCount > 1) {
        return { description: `${rootCount} accounts have UID 0.`, remediation: 'Remove or disable extra UID-0 accounts.' };
      }
      return null;
    },
  },
  {
    id: 'CYB-002',
    title: 'Sudo NOPASSWD rules present',
    category: 'users-auth',
    score: 6.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'sudo_config');
      if (!e) return null;
      if (e.data.nopasswd_rules > 0) {
        return {
          description: `${e.data.nopasswd_rules} NOPASSWD sudo rule(s) found.`,
          remediation: 'Remove NOPASSWD entries or restrict to specific commands.',
          metadata: { entries: e.data.nopasswd_entries },
        };
      }
      return null;
    },
  },
  {
    id: 'CYB-003',
    title: 'SSH private key with overly permissive permissions',
    category: 'users-auth',
    score: 7.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'ssh_keys');
      if (!e) return null;
      const bad = e.data.keys?.filter((k) => k.overly_permissive) || [];
      if (bad.length > 0) {
        return {
          description: `${bad.length} SSH private key(s) have permissions wider than 600.`,
          remediation: 'Run chmod 600 on private key files.',
          metadata: { files: bad.map((k) => k.file) },
        };
      }
      return null;
    },
  },

  // ── Network ────────────────────────────────────────────────────────
  {
    id: 'CYB-010',
    title: 'Service listening on all interfaces (0.0.0.0)',
    category: 'network',
    score: 5.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'listening_ports');
      if (!e) return null;
      const wildcard = e.data.ports?.filter((p) => p.address === '0.0.0.0' || p.address === '::' || p.address === '*') || [];
      if (wildcard.length > 0) {
        return {
          description: `${wildcard.length} service(s) listening on all interfaces.`,
          remediation: 'Bind services to specific interfaces or localhost where possible.',
          metadata: { services: wildcard },
        };
      }
      return null;
    },
  },
  {
    id: 'CYB-011',
    title: 'Firewall disabled or not detected',
    category: 'network',
    score: 6.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'firewall');
      if (!e) return null;
      const d = e.data;
      const enabled = d.pf_enabled || d.application_firewall === 'enabled' ||
        d.ufw_status === 'active' || (d.iptables_rules && d.iptables_rules > 5);
      if (!enabled) {
        return { description: 'No active firewall detected.', remediation: 'Enable the host firewall (ufw, pf, iptables).' };
      }
      return null;
    },
  },

  // ── Filesystem ─────────────────────────────────────────────────────
  {
    id: 'CYB-020',
    title: 'Excessive SUID binaries',
    category: 'filesystem',
    score: 5.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'suid_binaries');
      if (!e) return null;
      if (e.data.count > 30) {
        return {
          description: `${e.data.count} SUID binaries found (threshold: 30).`,
          remediation: 'Audit SUID binaries and remove the setuid bit where unnecessary.',
        };
      }
      return null;
    },
  },
  {
    id: 'CYB-021',
    title: 'World-writable directories without sticky bit',
    category: 'filesystem',
    score: 6.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'world_writable_dirs');
      if (!e) return null;
      if (e.data.count > 0) {
        return {
          description: `${e.data.count} world-writable directory/ies lack the sticky bit.`,
          remediation: 'Set the sticky bit (chmod +t) or restrict permissions.',
          metadata: { paths: e.data.paths?.slice(0, 10) },
        };
      }
      return null;
    },
  },
  {
    id: 'CYB-022',
    title: 'Sensitive file with weak permissions',
    category: 'filesystem',
    score: 7.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'sensitive_file_permissions');
      if (!e) return null;
      const weak = e.data.files?.filter((f) => {
        const perms = parseInt(f.permissions, 8);
        if (f.path.includes('shadow')) return perms > 0o640;
        return perms > 0o644;
      }) || [];
      if (weak.length > 0) {
        return {
          description: `${weak.length} sensitive file(s) have overly permissive access.`,
          remediation: 'Tighten file permissions (e.g. 640 for shadow, 644 for passwd).',
          metadata: { files: weak },
        };
      }
      return null;
    },
  },

  // ── Packages ───────────────────────────────────────────────────────
  {
    id: 'CYB-030',
    title: 'System package inventory collected',
    category: 'packages',
    score: 0.0, // informational
    evaluate(evidence) {
      const packageTypes = ['dpkg_packages', 'rpm_packages', 'apk_packages', 'homebrew_packages', 'pip_packages', 'npm_global_packages'];
      const found = evidence.filter((ev) => packageTypes.includes(ev.type));
      if (found.length > 0) {
        const total = found.reduce((sum, ev) => sum + (ev.data.count || 0), 0);
        return {
          description: `${total} packages inventoried across ${found.length} package manager(s).`,
          metadata: { managers: found.map((ev) => ({ type: ev.type, count: ev.data.count })) },
        };
      }
      return null;
    },
  },
];
