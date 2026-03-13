import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';

const RankingChart = ({ data }) => {
  if (!data || !data.ranked) return null;

  // Process data for TOPSIS bar chart
  const topsisData = useMemo(() => {
    return data.ranked.map(svc => ({
      name: svc.service_name,
      score: svc.closeness_coefficient,
      rank: svc.rank
    }));
  }, [data.ranked]);

  // Process data for QoS Radar Chart (comparing Top 3 services normalize values)
  const radarData = useMemo(() => {
    if (data.ranked.length === 0) return [];
    
    const criteriaList = data.criteria;
    const topServices = data.ranked.slice(0, 3); // Max 3 for Radar clarity
    
    // Find min/max for simple radar normalization (0-1) across raw values
    const boundaries = {};
    criteriaList.forEach(c => {
      const vals = data.ranked.map(s => Number(s[c]) || 0);
      boundaries[c] = { min: Math.min(...vals), max: Math.max(...vals) };
    });

    const formatCriteria = (c) => c.replace('_', ' ').toUpperCase();

    const chartData = criteriaList.map(c => {
      const dataPoint = { subject: formatCriteria(c), fullMark: 100 };
      topServices.forEach(svc => {
        const val = Number(svc[c]) || 0;
        let p = 0;
        if (boundaries[c].max > boundaries[c].min) {
           p = (val - boundaries[c].min) / (boundaries[c].max - boundaries[c].min) * 100;
        } else {
           p = 100;
        }
        
        // Reverse cost/response_time for the visual, so higher is always "better" visually?
        // Let's just plot the raw normalized spread
        if (c === 'cost' || c === 'response_time') {
           p = 100 - p; 
        }
        
        dataPoint[svc.service_name] = p;
      });
      return dataPoint;
    });

    return { chartData, topServices };
  }, [data]);

  const colors = ['#34d399', '#38bdf8', '#818cf8'];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
      
      {/* Chart 1: TOPSIS Scores */}
      <div className="glass-panel p-6 rounded-2xl h-96 flex flex-col">
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <span>📊</span> Comparative TOPSIS Score (C*)
        </h3>
        <div className="flex-1 w-full relative">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={topsisData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
              <XAxis type="number" domain={[0, 1]} stroke="#94a3b8" />
              <YAxis dataKey="name" type="category" width={100} stroke="#94a3b8" />
              <Tooltip 
                cursor={{ fill: '#1e293b' }} 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
                itemStyle={{ color: '#10b981', fontWeight: 'bold' }}
                formatter={(val) => Number(val).toFixed(4)}
              />
              <Bar 
                dataKey="score" 
                name="TOPSIS Score" 
                fill="#10b981" 
                radius={[0, 4, 4, 0]} 
                barSize={24}
                animationDuration={1500}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 2: QoS Radar mapping the top 3 */}
      {radarData.topServices.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl h-96 flex flex-col">
          <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
            <span>🕸️</span> Top 3: Quality of Service Matrix
          </h3>
          <p className="text-xs text-slate-400 mb-4 text-center">
            Normalized Performance (Higher/Outer edge is better)
          </p>
          <div className="flex-1 w-full mx-auto relative pointer-events-none sm:pointer-events-auto">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData.chartData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
                  formatter={(val) => `${Number(val).toFixed(0)}% Perf`}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                
                {radarData.topServices.map((svc, idx) => (
                  <Radar
                    key={svc.service_name}
                    name={svc.service_name}
                    dataKey={svc.service_name}
                    stroke={colors[idx % colors.length]}
                    fill={colors[idx % colors.length]}
                    fillOpacity={0.4}
                    animationDuration={2000}
                    animationBegin={idx * 300}
                  />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default RankingChart;
