import React, { useState } from 'react';

const ManualForm = ({ onAddSuccess }) => {
  const initForm = {
    serviceName: '',
    responseTime: '',
    throughput: '',
    security: '',
    cost: ''
  };

  const [formData, setFormData] = useState(initForm);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setError('');

    try {
      // Hits the db_bp in the backend
      const response = await api.post('/add_service', {
        service_name: formData.serviceName,
        response_time: parseFloat(formData.responseTime),
        throughput: parseFloat(formData.throughput),
        security: parseFloat(formData.security),
        cost: parseFloat(formData.cost)
      });
      
      if (response.data?.status === 'success') {
        setMessage('Service added successfully');
        setFormData(initForm);
        if (onAddSuccess) onAddSuccess();
      } else {
        setError(response.data?.message || 'Failed to add service');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error communicating with server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col h-full">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-blue-500/20 rounded-lg">
          <span className="text-xl">✍️</span>
        </div>
        <h3 className="text-xl font-semibold text-white">Manual Entry</h3>
      </div>
      
      {error && <div className="text-sm text-rose-400 bg-rose-500/10 p-2 rounded mb-4">{error}</div>}
      {message && <div className="text-sm text-emerald-400 bg-emerald-500/10 p-2 rounded mb-4">{message}</div>}

      <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
        <div className="grid grid-cols-2 gap-4 mb-5">
          <div className="col-span-2">
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Service Name</label>
            <input type="text" name="serviceName" required value={formData.serviceName} onChange={handleChange}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-400" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Response Time (ms)</label>
            <input type="number" step="any" name="responseTime" required value={formData.responseTime} onChange={handleChange}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-400" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Throughput (req/s)</label>
            <input type="number" step="any" name="throughput" required value={formData.throughput} onChange={handleChange}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-400" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Security (0-100)</label>
            <input type="number" step="any" name="security" required value={formData.security} onChange={handleChange}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-400" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Cost ($/mo)</label>
            <input type="number" step="any" name="cost" required value={formData.cost} onChange={handleChange}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-400" />
          </div>
        </div>
        
        <div className="mt-auto">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-700 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition-all disabled:opacity-50"
          >
            {loading ? 'Adding...' : 'Add Service manually'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ManualForm;
