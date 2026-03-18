// Register page — create account + tenant (§10.1)
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { register } from '../api/queries';
import { Button, Input } from '../components/ui';

export default function RegisterPage() {
  const fetchMe = useAuthStore((s) => s.fetchMe);
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', display_name: '', tenant_name: '', tenant_slug: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleTenantName = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    setForm((f) => ({ ...f, tenant_name: name, tenant_slug: slug }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(form);
      await fetchMe();
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center mb-1">BeGuardit</h1>
        <p className="text-sm text-slate-500 text-center mb-6">Create your account</p>

        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm border border-slate-200 space-y-4">
          {error && <p className="text-sm text-red-600 bg-red-50 p-2 rounded">{error}</p>}

          <Input label="Email" type="email" required value={form.email} onChange={update('email')} />
          <Input label="Password" type="password" required minLength={8} value={form.password} onChange={update('password')} />
          <Input label="Display name" value={form.display_name} onChange={update('display_name')} />
          <Input label="Organization name" required value={form.tenant_name} onChange={handleTenantName} />
          <Input label="Slug" required value={form.tenant_slug} onChange={update('tenant_slug')} pattern="^[a-z0-9][a-z0-9\-]*$" className="font-mono" />

          <Button type="submit" loading={loading} className="w-full">
            Create account
          </Button>
        </form>

        <p className="text-sm text-center mt-4 text-slate-500">
          Have an account? <Link to="/login" className="text-blue-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
