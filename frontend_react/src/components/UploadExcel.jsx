import React, { useState, useRef } from 'react';
import { api } from '../App';

const UploadExcel = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && (selected.name.endsWith('.xlsx') || selected.name.endsWith('.xls'))) {
      setFile(selected);
      setError('');
    } else {
      setFile(null);
      setError('Please select a valid Excel file (.xlsx or .xls)');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setLoading(true);
    setMessage('');
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Hits the services_bp in the backend
      const response = await api.post('/services/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data?.status === 'success') {
        setMessage(response.data.message || 'File uploaded successfully');
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
        if (onUploadSuccess) onUploadSuccess();
      } else {
        setError(response.data?.message || 'Upload failed');
      }
    } catch (err) {
      if (err.response?.status === 409) {
        setError('Upload stopped: One or more services already exist in the database.');
      } else {
        setError(err.response?.data?.message || 'Error communicating with server');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col h-full">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-emerald-500/20 rounded-lg">
          <span className="text-xl">📊</span>
        </div>
        <h3 className="text-xl font-semibold text-white">Bulk Upload</h3>
      </div>
      
      <p className="text-sm text-slate-400 mb-6">
        Upload an Excel file containing multiple cloud services.
        Required columns: Service, Response Time, Throughput, Security, Cost.
      </p>

      {error && <div className="text-sm text-rose-400 bg-rose-500/10 p-2 rounded mb-4">{error}</div>}
      {message && <div className="text-sm text-emerald-400 bg-emerald-500/10 p-2 rounded mb-4">{message}</div>}

      <div className="flex-1 flex flex-col justify-end">
        <div className="relative border-2 border-dashed border-slate-600 rounded-xl p-4 text-center hover:bg-white/5 transition-colors cursor-pointer group mb-4">
          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".xlsx, .xls"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <span className="text-slate-300 group-hover:text-white transition-colors">
            {file ? file.name : "Click or drag .xlsx file here"}
          </span>
        </div>
        
        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="w-full bg-slate-700 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Uploading...' : 'Upload Data'}
        </button>
      </div>
    </div>
  );
};

export default UploadExcel;
