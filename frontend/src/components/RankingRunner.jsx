import React, { useState } from 'react';
import { api } from '../App';

const RankingRunner = ({ servicesCount, onRankingSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRank = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Hits the /services/rank endpoint in the backend
      const response = await api.post('/services/rank');
      
      if (response.data?.status === 'success') {
        onRankingSuccess(response.data.data);
      } else {
        setError(response.data?.message || 'Ranking failed');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error communicating with server. Ensure at least 2 services exist.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-8 text-center relative overflow-hidden">
      {/* Decorative background gradient */}
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-blue-500/10 blur-xl pointer-events-none" />
      
      <div className="relative z-10 flex flex-col items-center max-w-2xl mx-auto">
        <h2 className="text-3xl font-bold text-white mb-4">Run Service Ranking</h2>
        <p className="text-slate-400 mb-8">
          Execute the Context Temporal Information & Fuzzy Entropy Weight TOPSIS algorithm across your <strong className="text-white">{servicesCount}</strong> stored cloud services to find the optimal provider.
        </p>
        
        {error && <div className="text-sm text-rose-400 bg-rose-500/10 px-4 py-2 rounded-lg mb-6 w-full">{error}</div>}

        <button
          onClick={handleRank}
          disabled={loading || servicesCount < 2}
          className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-lg font-semibold py-4 px-10 rounded-xl hover:shadow-[0_0_30px_rgba(16,185,129,0.3)] hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3"
        >
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Computing Models...
            </>
          ) : (
             '⚡ Execute TOPSIS Algorithm'
          )}
        </button>
        {servicesCount < 2 && (
          <p className="text-amber-400 text-xs mt-4">⚠️ You need at least 2 services to run the ranking algorithm.</p>
        )}
      </div>
    </div>
  );
};

export default RankingRunner;
