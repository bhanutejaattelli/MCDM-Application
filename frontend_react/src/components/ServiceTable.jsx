import React, { useState } from 'react';

const ServiceTable = ({ services, loading, onRefresh, currentPage, totalPages, onPageChange, totalCount }) => {
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ response_time: 0, throughput: 0, security: 0, cost: 0 });
  const [actionLoading, setActionLoading] = useState(false);

  const startEdit = (svc) => {
    setEditingId(svc.id);
    setEditForm({
      response_time: svc.response_time,
      throughput:    svc.throughput,
      security:      svc.security,
      cost:          svc.cost
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  const handleSave = async (id) => {
    setActionLoading(true);
    try {
      await api.put(`/update_service/${id}`, editForm);
      setEditingId(null);
      onRefresh();
    } catch (err) {
      alert("Failed to update service: " + (err.response?.data?.message || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete '${name}'?`)) return;
    
    setActionLoading(true);
    try {
      await api.delete(`/delete_service/${id}`);
      onRefresh();
    } catch (err) {
      alert("Failed to delete service: " + (err.response?.data?.message || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleChange = (e) => {
    setEditForm({ ...editForm, [e.target.name]: e.target.value });
  };

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <span className="text-xl">🗄️</span>
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">Stored Cloud Services</h3>
            <p className="text-xs text-slate-400 mt-1">Total Records: {totalCount || 0}</p>
          </div>
        </div>
        
        <button 
          onClick={onRefresh}
          disabled={loading || actionLoading}
          className="text-sm bg-white/5 hover:bg-white/10 text-slate-300 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
        >
          {loading ? '🔄 Refreshing...' : '🔄 Refresh'}
        </button>
      </div>

      <div className="overflow-x-auto mb-4">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-700 text-xs uppercase tracking-wider text-slate-400">
              <th className="p-4 font-medium">Service Name</th>
              <th className="p-4 font-medium whitespace-nowrap">Response (ms)</th>
              <th className="p-4 font-medium whitespace-nowrap">Throughput (r/s)</th>
              <th className="p-4 font-medium whitespace-nowrap">Security (0-100)</th>
              <th className="p-4 font-medium whitespace-nowrap">Cost ($/mo)</th>
              <th className="p-4 font-medium whitespace-nowrap">Added On</th>
              <th className="p-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="text-sm divide-y divide-slate-800/50">
            {services.length === 0 ? (
              <tr>
                <td colSpan="7" className="p-8 text-center text-slate-500">
                  No services found. Upload Excel or use Manual Entry to add services.
                </td>
              </tr>
            ) : (
              services.map((svc, idx) => {
                const isEditing = editingId === svc.id;
                return (
                  <tr key={svc.id || idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="p-4 text-white font-medium break-all">{svc.service_name}</td>
                    
                    {isEditing ? (
                      <>
                        <td className="p-4"><input type="number" name="response_time" value={editForm.response_time} onChange={handleChange} className="w-20 bg-slate-800/80 border border-purple-500/50 focus:border-purple-400 focus:ring-1 focus:ring-purple-400 rounded-md px-2 py-1.5 text-white shadow-inner outline-none transition-all" /></td>
                        <td className="p-4"><input type="number" name="throughput" value={editForm.throughput} onChange={handleChange} className="w-20 bg-slate-800/80 border border-purple-500/50 focus:border-purple-400 focus:ring-1 focus:ring-purple-400 rounded-md px-2 py-1.5 text-white shadow-inner outline-none transition-all" /></td>
                        <td className="p-4"><input type="number" name="security" value={editForm.security} onChange={handleChange} className="w-20 bg-slate-800/80 border border-purple-500/50 focus:border-purple-400 focus:ring-1 focus:ring-purple-400 rounded-md px-2 py-1.5 text-white shadow-inner outline-none transition-all" /></td>
                        <td className="p-4"><input type="number" name="cost" value={editForm.cost} onChange={handleChange} className="w-20 bg-slate-800/80 border border-purple-500/50 focus:border-purple-400 focus:ring-1 focus:ring-purple-400 rounded-md px-2 py-1.5 text-white shadow-inner outline-none transition-all" /></td>
                      </>
                    ) : (
                      <>
                        <td className="p-4 text-slate-300">{svc.response_time}</td>
                        <td className="p-4 text-slate-300">{svc.throughput}</td>
                        <td className="p-4 text-slate-300">{svc.security}</td>
                        <td className="p-4 text-slate-300">${svc.cost}</td>
                      </>
                    )}
                    
                    <td className="p-4 text-slate-500 text-xs whitespace-nowrap">
                      {new Date(svc.timestamp).toLocaleDateString()}
                    </td>
                    
                    <td className="p-4 text-right space-x-2 whitespace-nowrap">
                      {isEditing ? (
                        <>
                          <button onClick={() => handleSave(svc.id)} disabled={actionLoading} className="text-emerald-400 hover:text-emerald-300 bg-emerald-400/10 hover:bg-emerald-400/20 px-3 py-1.5 rounded-md transition-colors text-xs font-medium focus:ring-2 focus:ring-emerald-400 disabled:opacity-50">Save</button>
                          <button onClick={cancelEdit} disabled={actionLoading} className="text-slate-400 hover:text-slate-200 bg-slate-700/50 hover:bg-slate-700 px-3 py-1.5 rounded-md transition-colors text-xs font-medium disabled:opacity-50 tracking-wide">Cancel</button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => startEdit(svc)} disabled={actionLoading} className="text-blue-400 hover:text-blue-300 bg-blue-400/10 hover:bg-blue-400/20 px-3 py-1.5 rounded-md transition-colors text-xs font-medium focus:ring-2 focus:ring-blue-400 disabled:opacity-50">Edit</button>
                          <button onClick={() => handleDelete(svc.id, svc.service_name)} disabled={actionLoading} className="text-red-400 hover:text-red-300 bg-red-400/10 hover:bg-red-400/20 px-3 py-1.5 rounded-md transition-colors text-xs font-medium focus:ring-2 focus:ring-red-400 disabled:opacity-50">Delete</button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-700/50 mt-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1 || loading}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Previous
          </button>
          
          <span className="text-sm text-slate-400 font-medium">
            Page <span className="text-white">{currentPage}</span> of <span className="text-white">{totalPages}</span>
          </span>
          
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages || loading}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

export default ServiceTable;
