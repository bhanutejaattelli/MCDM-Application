import React, { useState, useEffect } from 'react';
import { api, useAuth } from '../App';
import Navbar from '../components/Navbar';
import { useNavigate } from 'react-router-dom';

const AdminDashboard = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('providers');

  // Redirect non-admins
  useEffect(() => {
    if (currentUser && currentUser.role !== 'admin') {
      navigate('/dashboard');
    }
  }, [currentUser, navigate]);

  const tabs = [
    { id: 'providers', label: '🌐 Global Providers', icon: '🌐' },
    { id: 'users', label: '👥 User Management', icon: '👥' },
    { id: 'refresh', label: '🔄 Data Refresh', icon: '🔄' },
    { id: 'logs', label: '📋 Update Logs', icon: '📋' },
  ];

  return (
    <div className="min-h-screen bg-slate-900 pb-20">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
        {/* Header */}
        <header>
          <h2 className="text-3xl font-bold text-white mb-2">👑 Admin Dashboard</h2>
          <p className="text-slate-400">
            Manage global cloud providers, users, and system updates.
          </p>
        </header>

        {/* Tab Navigation */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                  : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'providers' && <ProviderManagement />}
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'refresh' && <DataRefresh />}
        {activeTab === 'logs' && <UpdateLogs />}
      </main>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// PROVIDER MANAGEMENT TAB
// ═══════════════════════════════════════════════════════════════════════
const ProviderManagement = () => {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [editId, setEditId] = useState(null);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [form, setForm] = useState({
    name: '', provider: 'AWS', type: 'Compute',
    cost: '', response_time: '', throughput: '', security: '',
  });

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const res = await api.get('/global-providers');
      if (res.data?.status === 'success') {
        setProviders(res.data.data.providers || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProviders(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editId) {
        await api.put(`/global-providers/${editId}`, form);
        setMessage({ text: 'Provider updated.', type: 'success' });
      } else {
        await api.post('/global-providers', form);
        setMessage({ text: 'Provider added.', type: 'success' });
      }
      setShowForm(false);
      setEditId(null);
      setForm({ name: '', provider: 'AWS', type: 'Compute', cost: '', response_time: '', throughput: '', security: '' });
      fetchProviders();
    } catch (err) {
      setMessage({ text: err.response?.data?.message || 'Failed.', type: 'error' });
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this provider?')) return;
    try {
      await api.delete(`/global-providers/${id}`);
      setMessage({ text: 'Provider deleted.', type: 'success' });
      fetchProviders();
    } catch (err) {
      setMessage({ text: 'Delete failed.', type: 'error' });
    }
  };

  const startEdit = (p) => {
    setForm({
      name: p.name || '', provider: p.provider || 'AWS', type: p.type || 'Compute',
      cost: p.cost || '', response_time: p.response_time || '', throughput: p.throughput || '', security: p.security || '',
    });
    setEditId(p.id);
    setShowForm(true);
  };

  return (
    <div className="space-y-4">
      {message.text && (
        <div className={`p-3 rounded-lg text-sm border ${message.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
          {message.text}
        </div>
      )}

      <div className="flex justify-between items-center">
        <p className="text-slate-400 text-sm">{providers.length} total providers</p>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowUpload(!showUpload); setShowForm(false); }}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-all"
          >
            {showUpload ? '✖ Cancel Upload' : '📤 Bulk Upload'}
          </button>
          <button
            onClick={() => { setShowForm(!showForm); setShowUpload(false); setEditId(null); setForm({ name: '', provider: 'AWS', type: 'Compute', cost: '', response_time: '', throughput: '', security: '' }); }}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-all"
          >
            {showForm ? '✖ Cancel' : '➕ Add Provider'}
          </button>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-5 border border-white/5 space-y-4">
          <h3 className="text-white font-semibold">{editId ? '✏️ Edit Provider' : '➕ Add New Provider'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <input placeholder="Service Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500" />
            <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500">
              <option>AWS</option><option>Azure</option><option>GCP</option><option>Custom</option>
            </select>
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500">
              <option>Compute</option><option>Storage</option><option>Database</option><option>Network</option>
            </select>
            <input placeholder="Cost ($/hr)" type="number" step="any" value={form.cost} onChange={(e) => setForm({ ...form, cost: e.target.value })} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500" />
            <input placeholder="Response Time (ms)" type="number" step="any" value={form.response_time} onChange={(e) => setForm({ ...form, response_time: e.target.value })} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500" />
            <input placeholder="Throughput (req/s)" type="number" step="any" value={form.throughput} onChange={(e) => setForm({ ...form, throughput: e.target.value })} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500" />
            <input placeholder="Security (0-10)" type="number" step="any" value={form.security} onChange={(e) => setForm({ ...form, security: e.target.value })} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500" />
            <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-all">
              {editId ? '💾 Update' : '➕ Add'}
            </button>
          </div>
        </form>
      )}

      {/* Bulk Upload Area */}
      {showUpload && (
        <div className="glass-panel rounded-xl p-5 border border-white/5 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-white font-semibold">📤 Bulk Upload Providers</h3>
            <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">Excel</span>
          </div>
          <p className="text-slate-400 text-sm mb-4">
            Upload an Excel (.xlsx) file with columns EXACTLY matching:<br/>
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400 mr-1">Name</code> 
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400 mr-1">Provider</code> 
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400 mr-1">Type</code> 
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400 mr-1">Cost</code> 
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400 mr-1">Response Time</code> 
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400 mr-1">Throughput</code> 
            <code className="bg-slate-800 px-1 py-0.5 rounded text-purple-400">Security</code>
          </p>
          <div className="relative border-2 border-dashed border-slate-600 rounded-xl p-6 text-center hover:bg-white/5 transition-colors cursor-pointer group">
            <input 
              type="file" 
              accept=".xlsx, .xls"
              onChange={async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append('file', file);
                setMessage({ text: 'Uploading...', type: 'success' });
                try {
                  const res = await api.post('/global-providers/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                  });
                  if (res.data?.status === 'success') {
                    setMessage({ text: res.data.message, type: 'success' });
                    setShowUpload(false);
                    fetchProviders();
                  } else {
                    setMessage({ text: res.data?.message || 'Upload failed', type: 'error' });
                  }
                } catch (err) {
                  setMessage({ text: err.response?.data?.message || 'Error communicating with server', type: 'error' });
                }
                e.target.value = ''; // Reset input
              }}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="text-3xl mb-2">📁</div>
            <span className="text-slate-300 font-medium group-hover:text-white transition-colors">
              Click or drag .xlsx file here to upload
            </span>
          </div>
        </div>
      )}

      {/* Provider List */}
      <div className="glass-panel rounded-xl border border-white/5 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-3 text-slate-400 font-medium">Name</th>
                  <th className="text-left p-3 text-slate-400 font-medium">Provider</th>
                  <th className="text-left p-3 text-slate-400 font-medium">Type</th>
                  <th className="text-right p-3 text-slate-400 font-medium">Cost</th>
                  <th className="text-right p-3 text-slate-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p) => (
                  <tr key={p.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="p-3 text-white font-medium">{p.name}</td>
                    <td className="p-3 text-slate-300">{p.provider}</td>
                    <td className="p-3 text-slate-300">{p.type}</td>
                    <td className="p-3 text-right text-slate-300 font-mono">${typeof p.cost === 'number' ? p.cost.toFixed(4) : p.cost}</td>
                    <td className="p-3 text-right">
                      <button onClick={() => startEdit(p)} className="text-blue-400 hover:text-blue-300 text-xs mr-3 transition-colors">✏️ Edit</button>
                      <button onClick={() => handleDelete(p.id)} className="text-red-400 hover:text-red-300 text-xs transition-colors">🗑️ Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// USER MANAGEMENT TAB
// ═══════════════════════════════════════════════════════════════════════
const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/users');
      if (res.data?.status === 'success') {
        setUsers(res.data.data.users || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const promoteUser = async (targetEmail) => {
    try {
      const res = await api.post('/admin/make-admin', { email: targetEmail || email });
      setMessage({ text: res.data?.message || 'User promoted.', type: 'success' });
      setEmail('');
      fetchUsers();
    } catch (err) {
      setMessage({ text: err.response?.data?.message || 'Failed to promote.', type: 'error' });
    }
  };

  const demoteUser = async (targetEmail) => {
    if (!confirm(`Remove admin role from ${targetEmail}?`)) return;
    try {
      const res = await api.post('/admin/remove-admin', { email: targetEmail });
      setMessage({ text: res.data?.message || 'Role updated.', type: 'success' });
      fetchUsers();
    } catch (err) {
      setMessage({ text: err.response?.data?.message || 'Failed.', type: 'error' });
    }
  };

  return (
    <div className="space-y-4">
      {message.text && (
        <div className={`p-3 rounded-lg text-sm border ${message.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
          {message.text}
        </div>
      )}

      {/* Promote by email */}
      <div className="glass-panel rounded-xl p-5 border border-white/5">
        <h3 className="text-white font-semibold mb-3">👑 Promote User to Admin</h3>
        <div className="flex gap-3">
          <input
            type="email"
            placeholder="Enter user email..."
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
          />
          <button
            onClick={() => promoteUser()}
            disabled={!email}
            className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-40"
          >
            👑 Make Admin
          </button>
        </div>
      </div>

      {/* User List */}
      <div className="glass-panel rounded-xl border border-white/5 overflow-hidden">
        <div className="p-4 border-b border-white/10">
          <h3 className="text-white font-semibold">All Users ({users.length})</h3>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-3 text-slate-400 font-medium">Email</th>
                  <th className="text-left p-3 text-slate-400 font-medium">Display Name</th>
                  <th className="text-left p-3 text-slate-400 font-medium">Role</th>
                  <th className="text-left p-3 text-slate-400 font-medium">Last Login</th>
                  <th className="text-right p-3 text-slate-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.uid} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="p-3 text-white">{u.email}</td>
                    <td className="p-3 text-slate-300">{u.displayName || '—'}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.role === 'admin'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                          : 'bg-slate-700 text-slate-300 border border-slate-600'
                      }`}>
                        {u.role === 'admin' ? '👑 Admin' : '👤 User'}
                      </span>
                    </td>
                    <td className="p-3 text-slate-400 text-xs">{u.lastLoginAt || '—'}</td>
                    <td className="p-3 text-right">
                      {u.role === 'admin' ? (
                        <button onClick={() => demoteUser(u.email)} className="text-red-400 hover:text-red-300 text-xs transition-colors">
                          ⬇️ Remove Admin
                        </button>
                      ) : (
                        <button onClick={() => promoteUser(u.email)} className="text-amber-400 hover:text-amber-300 text-xs transition-colors">
                          ⬆️ Make Admin
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// DATA REFRESH TAB
// ═══════════════════════════════════════════════════════════════════════
const DataRefresh = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState({ text: '', type: '' });

  const triggerRefresh = async () => {
    setRefreshing(true);
    setMessage({ text: '', type: '' });
    setResult(null);
    try {
      const res = await api.post('/global-providers/refresh');
      if (res.data?.status === 'success') {
        setResult(res.data.data);
        setMessage({ text: res.data.message, type: 'success' });
      } else {
        setMessage({ text: res.data?.message || 'Refresh failed.', type: 'error' });
      }
    } catch (err) {
      setMessage({
        text: err.response?.data?.message || 'Refresh request failed.',
        type: 'error',
      });
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="glass-panel rounded-xl p-6 border border-white/5 text-center">
        <div className="text-5xl mb-4">🔄</div>
        <h3 className="text-xl font-bold text-white mb-2">Refresh Cloud Pricing Data</h3>
        <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
          Fetch the latest pricing data from AWS, Azure, and GCP using their free public APIs.
          This replaces all existing global provider data.
        </p>
        <button
          onClick={triggerRefresh}
          disabled={refreshing}
          className="px-8 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {refreshing ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
              Refreshing... (this may take a minute)
            </span>
          ) : (
            '🚀 Refresh Now'
          )}
        </button>
      </div>

      {message.text && (
        <div className={`p-4 rounded-xl text-sm border ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border-red-500/30 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      {result && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: 'AWS Services', value: result.aws_count, icon: '☁️', color: 'text-amber-400' },
            { label: 'Azure Services', value: result.azure_count, icon: '🔷', color: 'text-blue-400' },
            { label: 'GCP Services', value: result.gcp_count, icon: '🟢', color: 'text-emerald-400' },
          ].map((stat, i) => (
            <div key={i} className="glass-panel p-5 rounded-xl border border-white/5 text-center">
              <span className="text-3xl">{stat.icon}</span>
              <p className={`text-2xl font-bold mt-2 ${stat.color}`}>{stat.value}</p>
              <p className="text-slate-400 text-xs mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="glass-panel rounded-xl p-5 border border-white/5">
        <h3 className="text-white font-semibold mb-3">ℹ️ About Auto-Updates</h3>
        <ul className="text-slate-400 text-sm space-y-2">
          <li>• The system automatically refreshes pricing data every 24 hours when the backend is running.</li>
          <li>• All APIs used are <span className="text-emerald-400 font-medium">100% free</span> — no API keys or billing required.</li>
          <li>• Data sources: AWS Bulk Pricing API, Azure Retail Prices API, GCP Pricing Calculator.</li>
          <li>• QoS metrics (latency, throughput, security) are estimated using deterministic algorithms.</li>
        </ul>
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// UPDATE LOGS TAB
// ═══════════════════════════════════════════════════════════════════════
const UpdateLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api.get('/admin/update-logs');
        if (res.data?.status === 'success') {
          setLogs(res.data.data.logs || []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="glass-panel rounded-xl border border-white/5 overflow-hidden">
      <div className="p-4 border-b border-white/10">
        <h3 className="text-white font-semibold">📋 Recent Update Logs</h3>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent"></div>
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-3xl mb-2">📭</p>
          <p>No update logs yet. Trigger a refresh to see logs.</p>
        </div>
      ) : (
        <div className="divide-y divide-white/5">
          {logs.map((log) => (
            <div key={log.id} className="p-4 hover:bg-white/5 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  log.status === 'success'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-red-500/10 text-red-400 border border-red-500/30'
                }`}>
                  {log.status === 'success' ? '✅ Success' : '❌ Error'}
                </span>
                <span className="text-xs text-slate-500">{log.timestamp}</span>
              </div>
              <p className="text-sm text-slate-300">{log.message}</p>
              {log.status === 'success' && (
                <div className="flex gap-4 mt-2 text-xs text-slate-400">
                  <span>AWS: {log.aws_count || 0}</span>
                  <span>Azure: {log.azure_count || 0}</span>
                  <span>GCP: {log.gcp_count || 0}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


export default AdminDashboard;
