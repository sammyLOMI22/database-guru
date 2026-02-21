import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';

interface DatabaseConnection {
  id?: number;
  name: string;
  database_type: string;
  host?: string;
  port?: number;
  database_name: string;
  username?: string;
  password?: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (connection: DatabaseConnection) => void;
  connection?: DatabaseConnection;
}

export default function DatabaseConnectionModal({ isOpen, onClose, onSave, connection }: Props) {
  const [formData, setFormData] = useState<DatabaseConnection>(
    connection || {
      name: '',
      database_type: 'postgresql',
      host: 'localhost',
      port: 5432,
      database_name: '',
      username: '',
      password: '',
    }
  );

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showConnectionString, setShowConnectionString] = useState(false);

  if (!isOpen) return null;

  // Generate connection string for display
  const getConnectionString = (): string => {
    if (formData.database_type === 'sqlite') {
      return `sqlite:///${formData.database_name || '/path/to/database.db'}`;
    } else if (formData.database_type === 'duckdb') {
      return `duckdb:///${formData.database_name || '/path/to/database.duckdb'}`;
    } else if (formData.database_type === 'mongodb') {
      const user = formData.username || 'username';
      const pass = formData.password ? '****' : 'password';
      const host = formData.host || 'localhost';
      const port = formData.port || 27017;
      const db = formData.database_name || 'database';
      return `mongodb://${user}:${pass}@${host}:${port}/${db}`;
    } else if (formData.database_type === 'mysql') {
      const user = formData.username || 'username';
      const pass = formData.password ? '****' : 'password';
      const host = formData.host || 'localhost';
      const port = formData.port || 3306;
      const db = formData.database_name || 'database';
      return `mysql://${user}:${pass}@${host}:${port}/${db}`;
    } else if (formData.database_type === 'mssql') {
      const user = formData.username || 'sa';
      const pass = formData.password ? '****' : 'password';
      const host = formData.host || 'localhost';
      const port = formData.port || 1433;
      const db = formData.database_name || 'database';
      return `mssql+pymssql://${user}:${pass}@${host}:${port}/${db}`;
    } else if (formData.database_type === 'oracle') {
      const user = formData.username || 'system';
      const pass = formData.password ? '****' : 'password';
      const host = formData.host || 'localhost';
      const port = formData.port || 1521;
      const svc = formData.database_name || 'ORCL';
      return `oracle+oracledb://${user}:${pass}@${host}:${port}/?service_name=${svc}`;
    } else {
      // PostgreSQL (default)
      const user = formData.username || 'username';
      const pass = formData.password ? '****' : 'password';
      const host = formData.host || 'localhost';
      const port = formData.port || 5432;
      const db = formData.database_name || 'database';
      return `postgresql://${user}:${pass}@${host}:${port}/${db}`;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'port' ? parseInt(value) : value,
    }));
    setTestResult(null);
  };

  const handleDatabaseTypeChange = (type: string) => {
    const defaultPorts: Record<string, number> = {
      postgresql: 5432,
      mysql: 3306,
      sqlite: 0,
      mongodb: 27017,
      duckdb: 0,
      mssql: 1433,
      oracle: 1521,
    };
    setFormData((prev) => ({
      ...prev,
      database_type: type,
      port: defaultPorts[type] || 5432,
    }));
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    // Validate required fields
    if (!formData.name || !formData.name.trim()) {
      setTestResult({
        success: false,
        message: 'Connection name is required',
      });
      return;
    }

    if (!formData.database_name || !formData.database_name.trim()) {
      setTestResult({
        success: false,
        message: (formData.database_type === 'sqlite' || formData.database_type === 'duckdb')
          ? 'Database file path is required'
          : 'Database name is required',
      });
      return;
    }

    // For non-SQLite and non-DuckDB, validate host and port
    if (formData.database_type !== 'sqlite' && formData.database_type !== 'duckdb') {
      if (!formData.host || !formData.host.trim()) {
        setTestResult({
          success: false,
          message: 'Host is required',
        });
        return;
      }
      if (!formData.port || formData.port <= 0) {
        setTestResult({
          success: false,
          message: 'Valid port number is required',
        });
        return;
      }
      if (!formData.username || !formData.username.trim()) {
        setTestResult({
          success: false,
          message: 'Username is required',
        });
        return;
      }
    }

    setTesting(true);
    setTestResult(null);

    try {
      // Build request payload, excluding empty fields for SQLite
      const payload: any = {
        name: formData.name.trim(),
        database_type: formData.database_type,
        database_name: formData.database_name.trim(),
      };

      // Only include host/port/username/password for non-SQLite and non-DuckDB databases
      if (formData.database_type !== 'sqlite' && formData.database_type !== 'duckdb') {
        payload.host = formData.host || 'localhost';
        payload.port = formData.port || 5432;
        payload.username = formData.username || '';
        payload.password = formData.password || '';
      }

      // Call backend to test connection
      const response = await fetch('/api/connections/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        setTestResult({
          success: false,
          message: errorData.detail || `Connection test failed (${response.status})`,
        });
        return;
      }

      const data = await response.json();
      setTestResult({
        success: true,
        message: data.message || 'Connection successful!',
      });
    } catch (error: any) {
      console.error('Connection test error:', error);
      setTestResult({
        success: false,
        message: `Error: ${error.message || 'Failed to test connection'}`,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] backdrop-blur-xl animate-fadeIn p-4">
      <div className="glass-panel bg-white/5 dark:bg-black/40 rounded-[2.5rem] shadow-2xl border-white/10 max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col relative transition-all duration-500 scale-100 shadow-[0_30px_100px_rgba(0,0,0,0.5)]">
        {/* Glow Effects */}
        <div className="absolute top-0 left-0 w-64 h-64 bg-blue-500/5 blur-[100px] -ml-32 -mt-32 pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-64 h-64 bg-purple-500/5 blur-[100px] -mr-32 -mb-32 pointer-events-none" />

        <div className="flex items-center justify-between p-8 border-b border-white/5 bg-white/5 dark:bg-black/20">
          <div>
            <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 mb-2">Database Engine</h2>
            <h3 className="text-2xl font-black uppercase tracking-tight text-gray-900 dark:text-white">
              {connection ? 'Edit Connection' : 'Register New Connection'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-3 text-gray-400 hover:text-gray-200 glass-panel rounded-2xl hover:scale-110 active:scale-95 transition-all shadow-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto custom-scrollbar p-8 space-y-8 bg-transparent flex flex-col">
          {/* Connection Name */}
          <div className="space-y-3">
            <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
              Connection Identifier *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="e.g., Production Analytics"
              className="w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold"
            />
          </div>

          {/* Database Type */}
          <div className="space-y-4">
            <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
              Select Protocol *
            </label>
            <div className="flex flex-wrap gap-2.5">
              {['postgresql', 'mysql', 'sqlite', 'mssql', 'oracle', 'mongodb', 'duckdb'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleDatabaseTypeChange(type)}
                  className={`px-4 py-2.5 rounded-xl border-2 text-[11px] font-black uppercase tracking-widest transition-all duration-300 ${formData.database_type === type
                    ? 'border-blue-500/50 bg-blue-500/20 text-blue-500 shadow-[0_5px_15px_rgba(59,130,246,0.2)] scale-105'
                    : 'border-white/5 glass-panel bg-black/5 dark:bg-white/5 text-gray-500 hover:border-white/10 hover:text-gray-300'
                    }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic Fields */}
          {(formData.database_type === 'sqlite' || formData.database_type === 'duckdb') ? (
            <div className="space-y-3">
              <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
                Database Target Path *
              </label>
              <input
                type="text"
                name="database_name"
                value={formData.database_name}
                onChange={handleChange}
                required
                placeholder={formData.database_type === 'duckdb' ? 'e.g., /data/analytics.duckdb' : 'e.g., /data/local.db'}
                className="w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold"
              />
              {formData.database_type === 'duckdb' && (
                <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-xl text-[11px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                  Tip: Use :memory: for an ephemeral in-memory database
                </div>
              )}
            </div>
          ) : (
            <>
              {/* Host and Port */}
              <div className="flex flex-col md:flex-row gap-6">
                <div className="flex-1 space-y-3">
                  <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Host Address *</label>
                  <input
                    type="text"
                    name="host"
                    value={formData.host}
                    onChange={handleChange}
                    required
                    placeholder="localhost"
                    className="w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold"
                  />
                </div>
                <div className="w-full md:w-32 space-y-3">
                  <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Port *</label>
                  <input
                    type="number"
                    name="port"
                    value={formData.port}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all font-bold text-center"
                  />
                </div>
              </div>

              {/* Database Name / Service Name */}
              <div className="space-y-3">
                <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
                  {formData.database_type === 'oracle' ? 'Service Name *' : 'Database Schema Name *'}
                </label>
                <input
                  type="text"
                  name="database_name"
                  value={formData.database_name}
                  onChange={handleChange}
                  required
                  placeholder={formData.database_type === 'oracle' ? 'e.g., ORCL or XEPDB1' : 'e.g., app_production'}
                  className="w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold"
                />
                {formData.database_type === 'oracle' && (
                  <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-xl text-[11px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    Tip: Use the Oracle service name (e.g., ORCL, XEPDB1) — not the SID
                  </div>
                )}
              </div>

              {/* Username and Password */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
                    Authority Username *
                  </label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    required
                    placeholder="e.g., db_admin"
                    className="w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold"
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
                    Authority Secret *
                  </label>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    placeholder="••••••••"
                    className="w-full px-6 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold font-mono"
                  />
                </div>
              </div>
            </>
          )}

          {/* Connection String Preview */}
          <div className="border-t border-white/5 pt-8">
            <div className="flex items-center justify-between mb-4">
              <label className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
                Connection String Protocol
              </label>
              <button
                type="button"
                onClick={() => setShowConnectionString(!showConnectionString)}
                className="text-[11px] font-black uppercase tracking-widest text-blue-500 hover:text-blue-400 transition-colors"
              >
                {showConnectionString ? 'Hide Protocol' : 'Inspect Protocol'}
              </button>
            </div>
            {showConnectionString && (
              <div className="mt-2 p-6 glass-panel bg-black/20 dark:bg-black/40 rounded-2xl border-white/5 animate-slideDown overflow-hidden">
                <code className="text-[11px] text-blue-400/90 break-all font-mono leading-relaxed block">
                  {getConnectionString()}
                </code>
                <p className="mt-4 text-[11px] font-black uppercase tracking-widest text-gray-500">
                  Synchronized protocol string for engine registration. Password tokens are protected.
                </p>
              </div>
            )}
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className={`p-4 rounded-lg transition-colors ${testResult.success
                ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800/50'
                : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800/50'
                }`}
            >
              <p className="font-medium text-[11px] font-black uppercase tracking-widest">{testResult.message}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-4 pt-8 border-t border-white/5 mt-auto pb-4">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="px-6 py-4 glass-panel border-white/10 text-[11px] font-black uppercase tracking-widest text-gray-900 dark:text-white hover:bg-white/5 transition-all disabled:opacity-30 disabled:cursor-not-allowed group flex items-center gap-2"
            >
              {testing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {testing ? 'Verifying...' : 'Verify Engine'}
            </button>
            <div className="flex-1" />
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-4 text-[11px] font-black uppercase tracking-widest text-gray-500 hover:text-gray-300 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-8 py-4 bg-blue-600 text-white text-[11px] font-black uppercase tracking-widest rounded-2xl hover:bg-blue-500 transition-all shadow-xl shadow-blue-500/20 active:scale-95"
            >
              Synchronize connection
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
