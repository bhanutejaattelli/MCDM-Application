import React from 'react';
import { useAuth, api } from '../App';
import { useNavigate } from 'react-router-dom';

const Navbar = () => {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="glass-panel sticky top-0 z-50 border-b border-white/10 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🌟</span>
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent hidden sm:block">
            CloudRank AI
          </h1>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="text-sm text-slate-300">
            Welcome, <span className="font-semibold text-white">{currentUser?.displayName || currentUser?.email || 'User'}</span>
          </div>
          <button
            onClick={handleLogout}
            className="text-sm font-medium text-slate-400 hover:text-rose-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
          >
            Logout 👋
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
