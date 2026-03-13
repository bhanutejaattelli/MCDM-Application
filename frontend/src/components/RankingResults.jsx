import React from 'react';

const RankingResults = ({ data }) => {
  if (!data || !data.ranked) return null;
  const { ranked, best, weights } = data;

  return (
    <div className="glass-panel rounded-2xl p-6 md:p-8 animate-in mt-8">
      {/* Best Recommendation Card */}
      <div className="bg-gradient-to-br from-emerald-500/20 to-teal-900/40 border border-emerald-500/30 rounded-xl p-6 mb-8 flex flex-col md:flex-row items-center justify-between shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-3xl">🏆</span>
            <h3 className="text-emerald-400 font-bold tracking-wider text-sm">RECOMMENDED CLOUD SERVICE</h3>
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-2">{best}</h2>
          <p className="text-slate-300 text-sm max-w-lg">
            Based on Context Temporal Information Data and calculated fuzzy entropy weights, <strong>{best}</strong> offers the mathematically optimal balance between Response Time, Throughput, Security, and Cost.
          </p>
        </div>
        <div className="mt-6 md:mt-0 text-center md:text-right">
            <p className="text-5xl font-black bg-gradient-to-r from-emerald-300 to-teal-300 bg-clip-text text-transparent drop-shadow-lg">
              #{ranked[0]?.rank}
            </p>
            <p className="text-slate-400 text-xs mt-2 uppercase tracking-widest font-bold">TOPSIS Rank</p>
        </div>
      </div>

      {/* Extracted Entropy Weights */}
      <div className="mb-8 p-5 bg-slate-800/50 rounded-xl border border-white/5">
        <h4 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider flex items-center gap-2">
          <span className="text-blue-400">⚖️</span> Objective Entropy Weights
        </h4>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(weights).map(([criteria, weight]) => (
            <div key={criteria} className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
              <span className="block text-xs text-slate-400 capitalize mb-1">{criteria.replace('_', ' ')}</span>
              <span className="text-lg font-mono text-blue-300">{(weight * 100).toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Comprehensive Results Table */}
      <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
        <span>📋</span> Detailed TOPSIS Rankings
      </h3>
      <div className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-900/30 backdrop-blur-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-800/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-700">
              <th className="p-4 font-medium sticky left-0 bg-slate-800/90 z-10 w-24 text-center">🏆 Rank</th>
              <th className="p-4 font-medium">Service</th>
              <th className="p-4 font-medium">TOPSIS Score (C*)</th>
              <th className="p-4 font-medium hidden sm:table-cell">D+ (Ideal)</th>
              <th className="p-4 font-medium hidden sm:table-cell">D- (Anti-Ideal)</th>
            </tr>
          </thead>
          <tbody className="text-sm divide-y divide-slate-800">
            {ranked.map((svc, idx) => (
              <tr 
                key={`${svc.service_name}-${idx}`} 
                className={`transition-colors ${idx === 0 ? 'bg-emerald-500/10 hover:bg-emerald-500/20' : 'hover:bg-white/5'}`}
              >
                <td className="p-4 sticky left-0 font-bold text-center z-10 
                  ${idx === 0 ? 'bg-emerald-900/90 text-emerald-400' : 'bg-slate-900/90 text-slate-300'}"
                  style={{
                    backgroundColor: idx === 0 ? 'rgba(6, 78, 59, 0.8)' : 'rgba(15, 23, 42, 0.8)'
                  }}
                >
                  #{svc.rank}
                </td>
                <td className="p-4 text-white font-medium">{svc.service_name}</td>
                <td className="p-4 font-mono text-emerald-300 font-bold">
                  {Number(svc.closeness_coefficient).toFixed(4)}
                </td>
                <td className="p-4 font-mono text-slate-400 hidden sm:table-cell">{Number(svc.d_positive).toFixed(4)}</td>
                <td className="p-4 font-mono text-slate-400 hidden sm:table-cell">{Number(svc.d_negative).toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RankingResults;
