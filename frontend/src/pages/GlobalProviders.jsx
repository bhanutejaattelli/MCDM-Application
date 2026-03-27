import React, { useState, useEffect } from 'react';
import { api, useAuth } from '../App';
import Navbar from '../components/Navbar';

const GlobalProviders = () => {
  const { currentUser } = useAuth();
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [providerFilter, setProviderFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });

  const fetchProviders = async () => {
    setLoading(true);
    try {
      let url = '/global-providers?';
      if (providerFilter) url += `provider=${providerFilter}&`;
      if (typeFilter) url += `type=${typeFilter}&`;
      if (searchQuery) url += `search=${encodeURIComponent(searchQuery)}&`;

      const res = await api.get(url);
      if (res.data?.status === 'success') {
        setProviders(res.data.data.providers || []);
      }
    } catch (err) {
      console.error('Failed to fetch global providers:', err);
      setMessage({ text: 'Failed to fetch providers.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, [providerFilter, typeFilter]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => fetchProviders(), 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === providers.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(providers.map((p) => p.id)));
    }
  };

  const handleImport = async (importAll = false) => {
    setImporting(true);
    setMessage({ text: '', type: '' });
    try {
      const body = importAll ? {} : { provider_ids: Array.from(selectedIds) };
      const res = await api.post('/services/import-global', body);
      if (res.data?.status === 'success') {
        const d = res.data.data;
        setMessage({
          text: `✅ ${d.imported_count} services imported. ${d.skipped > 0 ? `${d.skipped} duplicate(s) skipped.` : ''}`,
          type: 'success',
        });
        setSelectedIds(new Set());
      }
    } catch (err) {
      setMessage({
        text: err.response?.data?.message || 'Import failed.',
        type: 'error',
      });
    } finally {
      setImporting(false);
    }
  };

  const providerColors = {
    AWS: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    Azure: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    GCP: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    Custom: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  };

  return (
    <div className="min-h-screen bg-slate-900 pb-20">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
        {/* Header */}
        <header>
          <h2 className="text-3xl font-bold text-white mb-2">🌐 Global Cloud Providers</h2>
          <p className="text-slate-400">
            Browse cloud services from AWS, Azure & GCP. Import them into your personal workspace for MCDM ranking.
          </p>
        </header>

        {/* Message */}
        {message.text && (
          <div
            className={`p-3 rounded-lg text-sm border ${
              message.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-red-500/10 border-red-500/30 text-red-400'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Filters + Actions Bar */}
        <div className="glass-panel rounded-xl p-4 border border-white/5">
          <div className="flex flex-wrap gap-3 items-center">
            {/* Search */}
            <input
              type="text"
              placeholder="🔍 Search services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 min-w-[200px] bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-400 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all text-sm"
            />

            {/* Provider filter */}
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
            >
              <option value="">All Providers</option>
              <option value="AWS">AWS</option>
              <option value="Azure">Azure</option>
              <option value="GCP">GCP</option>
            </select>

            {/* Type filter */}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
            >
              <option value="">All Types</option>
              <option value="Compute">Compute</option>
              <option value="Storage">Storage</option>
              <option value="Database">Database</option>
              <option value="Network">Network</option>
            </select>

            {/* Import buttons */}
            <div className="flex gap-2 ml-auto">
              <button
                onClick={() => handleImport(false)}
                disabled={importing || selectedIds.size === 0}
                className="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {importing ? '⏳ Importing...' : `📥 Import Selected (${selectedIds.size})`}
              </button>
              <button
                onClick={() => handleImport(true)}
                disabled={importing || providers.length === 0}
                className="px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {importing ? '⏳ Importing...' : '📥 Import All'}
              </button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Services', value: providers.length, icon: '📦', color: 'text-blue-400' },
            {
              label: 'AWS',
              value: providers.filter((p) => p.provider === 'AWS').length,
              icon: '☁️',
              color: 'text-amber-400',
            },
            {
              label: 'Azure',
              value: providers.filter((p) => p.provider === 'Azure').length,
              icon: '🔷',
              color: 'text-blue-400',
            },
            {
              label: 'GCP',
              value: providers.filter((p) => p.provider === 'GCP').length,
              icon: '🟢',
              color: 'text-emerald-400',
            },
          ].map((stat, i) => (
            <div
              key={i}
              className="glass-panel p-4 rounded-xl border border-white/5 flex items-center gap-3"
            >
              <span className="text-2xl">{stat.icon}</span>
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider">{stat.label}</p>
                <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="glass-panel rounded-xl border border-white/5 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent"></div>
              <span className="ml-3 text-slate-400">Loading providers...</span>
            </div>
          ) : providers.length === 0 ? (
            <div className="text-center py-20 text-slate-400">
              <p className="text-4xl mb-3">📭</p>
              <p className="text-lg font-medium">No global providers found</p>
              <p className="text-sm mt-1">
                {currentUser?.role === 'admin'
                  ? 'Go to Admin Dashboard to refresh pricing data.'
                  : 'Ask an admin to refresh the pricing data.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left p-3 text-slate-400 font-medium">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === providers.length && providers.length > 0}
                        onChange={selectAll}
                        className="rounded border-slate-600 bg-slate-800 text-purple-500 focus:ring-purple-500"
                      />
                    </th>
                    <th className="text-left p-3 text-slate-400 font-medium">Service Name</th>
                    <th className="text-left p-3 text-slate-400 font-medium">Provider</th>
                    <th className="text-left p-3 text-slate-400 font-medium">Type</th>
                    <th className="text-right p-3 text-slate-400 font-medium">Cost ($/hr)</th>
                    <th className="text-right p-3 text-slate-400 font-medium">Latency (ms)</th>
                    <th className="text-right p-3 text-slate-400 font-medium">Throughput</th>
                    <th className="text-right p-3 text-slate-400 font-medium">Security</th>
                  </tr>
                </thead>
                <tbody>
                  {providers.map((p) => (
                    <tr
                      key={p.id}
                      className={`border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer ${
                        selectedIds.has(p.id) ? 'bg-purple-500/5' : ''
                      }`}
                      onClick={() => toggleSelect(p.id)}
                    >
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(p.id)}
                          onChange={() => toggleSelect(p.id)}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded border-slate-600 bg-slate-800 text-purple-500 focus:ring-purple-500"
                        />
                      </td>
                      <td className="p-3 text-white font-medium">{p.name}</td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                            providerColors[p.provider] || providerColors.Custom
                          }`}
                        >
                          {p.provider}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300">{p.type}</td>
                      <td className="p-3 text-right text-slate-300 font-mono">
                        ${typeof p.cost === 'number' ? p.cost.toFixed(4) : p.cost}
                      </td>
                      <td className="p-3 text-right text-slate-300 font-mono">
                        {p.response_time || '—'}
                      </td>
                      <td className="p-3 text-right text-slate-300 font-mono">
                        {p.throughput || '—'}
                      </td>
                      <td className="p-3 text-right text-slate-300 font-mono">
                        {p.security || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default GlobalProviders;
