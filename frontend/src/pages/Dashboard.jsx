import React, { useState, useEffect } from 'react';
import { api } from '../App';
import Navbar from '../components/Navbar';
import UploadExcel from '../components/UploadExcel';
import ManualForm from '../components/ManualForm';
import ServiceTable from '../components/ServiceTable';
import RankingRunner from '../components/RankingRunner';
import RankingResults from '../components/RankingResults';
import RankingChart from '../components/RankingChart';
import Chatbot from '../components/Chatbot';

const Dashboard = () => {
  const [services, setServices] = useState([]);
  const [rankingData, setRankingData] = useState(null);
  const [loadingServices, setLoadingServices] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [avgResponseTime, setAvgResponseTime] = useState(0);
  const [avgThroughput, setAvgThroughput] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch services on load
  const fetchServices = async (page = 1) => {
    setLoadingServices(true);
    try {
      const response = await api.get(`/services?page=${page}&limit=10&search=${encodeURIComponent(searchQuery)}`);
      if (response.data?.status === 'success') {
        const d = response.data.data;
        setServices(d.services || []);
        setCurrentPage(d.page || 1);
        setTotalPages(d.total_pages || 1);
        setTotalCount(d.count || 0);
        setAvgResponseTime(d.avg_response_time || 0);
        setAvgThroughput(d.avg_throughput || 0);
      }
    } catch (err) {
      console.error('Failed to fetch services', err);
    } finally {
      setLoadingServices(false);
    }
  };

  // Fetch when page changes
  useEffect(() => {
    fetchServices(currentPage);
  }, [currentPage]);

  // Debounced fetch when search changes
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (currentPage !== 1) {
        setCurrentPage(1); // Will trigger the other useEffect
      } else {
        fetchServices(1);
      }
    }, 400);
    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const handleRefresh = () => fetchServices(currentPage);
  const handlePageChange = (newPage) => setCurrentPage(newPage);
  const handleAddSuccess = () => fetchServices(1); // Jump to page 1 on new add

  return (
    <div className="min-h-screen bg-slate-900 pb-20">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Header Section */}
        <header className="mb-10">
          <h2 className="text-3xl font-bold text-white mb-2">Service Dashboard</h2>
          <p className="text-slate-400">Manage your cloud services, run MCDM rankings, and visualize results.</p>
        </header>

        {/* Top Data Entry Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <UploadExcel onUploadSuccess={handleAddSuccess} />
          <ManualForm onAddSuccess={handleAddSuccess} />
        </div>

        {/* Statistics Cards */}
        <StatsCards 
          totalCount={totalCount}
          avgResponseTime={avgResponseTime}
          avgThroughput={avgThroughput}
          rankingData={rankingData}
        />

        {/* Services Table with Search */}
        <div className="space-y-4">
          <div className="flex px-2 relative z-10">
            <input 
              type="text" 
              placeholder="🔍 Search services by name..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full md:w-1/3 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all font-medium"
            />
          </div>
          
          <ServiceTable 
            services={services} 
            loading={loadingServices} 
            onRefresh={handleRefresh}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            totalCount={totalCount}
          />
        </div>

        {/* Ranking Execution */}
        <RankingRunner 
          servicesCount={totalCount} 
          onRankingSuccess={(data) => setRankingData(data)} 
        />

        {/* Results & Visualizations (Only show if ranking run) */}
        {rankingData && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <RankingResults data={rankingData} />
            <RankingChart data={rankingData} />
          </div>
        )}

      </main>
      <Chatbot />
    </div>
  );
};


// --- STATS CARDS MIGRATED ---

const StatsCards = ({ totalCount, avgResponseTime, avgThroughput, rankingData }) => {
  const bestService = rankingData?.best || 'Run Ranking';
  
  const stats = [
    { label: 'Total Services', value: totalCount, icon: '📦', color: 'text-blue-400' },
    { label: 'Avg Latency', value: `${avgResponseTime || 0} ms`, icon: '⚡', color: 'text-amber-400' },
    { label: 'Avg Throughput', value: `${avgThroughput || 0} req/s`, icon: '🚀', color: 'text-emerald-400' },
    { label: 'Best Service (TOPSIS)', value: bestService, icon: '🏆', color: 'text-purple-400' },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {stats.map((stat, idx) => (
        <div key={idx} className="glass-panel p-5 rounded-xl flex items-center gap-4 border border-white/5 relative overflow-hidden group hover:border-white/10 transition-colors">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-0 blur-2xl group-hover:opacity-5 transition-opacity rounded-full -translate-y-1/2 translate-x-1/2"></div>
          
          <div className={`p-3 rounded-lg bg-slate-800/80 ${stat.color} flex-shrink-0 border border-white/5 shadow-inner`}>
            <span className="text-2xl drop-shadow-sm">{stat.icon}</span>
          </div>
          
          <div className="z-10 min-w-0">
            <p className="text-xs text-slate-400 font-medium mb-1 uppercase tracking-wider">{stat.label}</p>
            <h4 className="text-xl font-bold text-white tracking-tight truncate">{stat.value}</h4>
          </div>
        </div>
      ))}
    </div>
  );
};


export default Dashboard;
