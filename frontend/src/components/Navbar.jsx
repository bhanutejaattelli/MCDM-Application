import React from 'react';
import { useAuth, api } from '../App';
import { useNavigate, useLocation } from 'react-router-dom';

const Navbar = () => {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  const navLinks = [
    { path: '/dashboard', label: '📊 Dashboard', show: true },
    { path: '/global-providers', label: '🌐 Global Providers', show: true },
    { path: '/admin', label: '👑 Admin', show: currentUser?.role === 'admin' },
  ];

  return (
    <nav className="glass-panel sticky top-0 z-50 border-b border-white/10 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Logo */}
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/dashboard')}>
            <span className="text-2xl">🌟</span>
            <h1 className="text-lg font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent hidden sm:block">
              CloudRank AI
            </h1>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks
              .filter((link) => link.show)
              .map((link) => (
                <button
                  key={link.path}
                  onClick={() => navigate(link.path)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive(link.path)
                      ? 'bg-white/10 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {link.label}
                </button>
              ))}
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-300 flex items-center gap-2">
            <span>
              Welcome, <span className="font-semibold text-white">{currentUser?.displayName || currentUser?.email || 'User'}</span>
            </span>
            {currentUser?.role === 'admin' && (
              <span className="px-1.5 py-0.5 bg-amber-500/10 text-amber-400 text-xs font-medium rounded-full border border-amber-500/30">
                Admin
              </span>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="text-sm font-medium text-slate-400 hover:text-rose-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
          >
            Logout 👋
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="flex md:hidden items-center gap-1 mt-2 overflow-x-auto pb-1">
        {navLinks
          .filter((link) => link.show)
          .map((link) => (
            <button
              key={link.path}
              onClick={() => navigate(link.path)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                isActive(link.path)
                  ? 'bg-white/10 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {link.label}
            </button>
          ))}
      </div>
    </nav>
  );
};

export default Navbar;

