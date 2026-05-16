import { useState, useEffect } from 'react';
import { X, Loader2, Shield } from 'lucide-react';
import { dmlAPI } from '../services/dmlApi';

interface DatabaseConnection {
  id?: number;
  name: string;
  database_type: string;
  host?: string;
  port?: number;
  database_name: string;
  username?: string;
  password?: string;
  /** Phase 25 — Neo4j only. NULL for other types. */
  encrypted?: boolean | null;
  /** Phase 25 — Neo4j only. Defaults true; defense-in-depth read-only enforcement. */
  read_only?: boolean | null;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (connection: DatabaseConnection) => void;
  connection?: DatabaseConnection;
}

const FILE_PATH_TYPES = ['sqlite', 'duckdb'];
const inputClass = "w-full px-4 py-4 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500 font-bold";
const labelClass = "text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400";

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

  // Write permissions state
  const [allowInsert, setAllowInsert] = useState(false);
  const [allowUpdate, setAllowUpdate] = useState(false);
  const [allowDelete, setAllowDelete] = useState(false);
  const [requireWhere, setRequireWhere] = useState(true);
  const [maxRows, setMaxRows] = useState(100);

  // Load existing write permissions when editing
  useEffect(() => {
    if (!isOpen || !connection?.id) return;
    dmlAPI.getPermissions(connection.id)
      .then((perms) => {
        setAllowInsert(perms.allow_insert);
        setAllowUpdate(perms.allow_update);
        setAllowDelete(perms.allow_delete);
        setRequireWhere(perms.require_where_clause);
        setMaxRows(perms.max_rows_per_operation);
      })
      .catch(() => { /* no permissions yet */ });
  }, [isOpen, connection?.id]);

  if (!isOpen) return null;

  // Generate connection string for display
  const getConnectionString = (): string => {
    const host = formData.host || 'localhost';
    const port = formData.port || 5432;
    const user = formData.username || 'username';
    const pass = formData.password ? '****' : 'password';
    const db = formData.database_name || 'database';

    switch (formData.database_type) {
      case 'sqlite':
        return `sqlite:///${formData.database_name || '/path/to/database.db'}`;
      case 'duckdb':
        return `duckdb:///${formData.database_name || '/path/to/database.duckdb'}`;
      case 'mongodb':
        return `mongodb://${user}:${pass}@${host}:${formData.port || 27017}/${db}`;
      case 'mysql':
        return `mysql://${user}:${pass}@${host}:${formData.port || 3306}/${db}`;
      case 'mssql':
        return `mssql+pymssql://${user}:${pass}@${host}:${formData.port || 1433}/${db}`;
      case 'oracle':
        return `oracle+oracledb://${user}:${pass}@${host}:${formData.port || 1521}/?service_name=${formData.database_name || 'ORCL'}`;
      case 'redis': {
        const authPart = formData.password ? `:****@` : '';
        const dbNum = formData.database_name || '0';
        return `redis://${authPart}${host}:${formData.port || 6379}/${dbNum}`;
      }
      case 'cassandra':
        return `cassandra://${user}:${pass}@${host}:${formData.port || 9042}/${db}`;
      case 'dynamodb': {
        const region = formData.host || 'us-east-1';
        const accessKey = formData.username || 'AKIA...';
        return `dynamodb://${region} (Access Key: ${accessKey})`;
      }
      case 'elasticsearch': {
        const authStr = formData.username ? `${user}:${pass}@` : '';
        const esScheme = formData.username ? 'https' : 'http';
        return `${esScheme}://${authStr}${host}:${formData.port || 9200}`;
      }
      case 'neo4j': {
        // host carries the full Bolt URI (e.g. bolt://localhost:7687 or neo4j+s://x.databases.neo4j.io)
        const uri = formData.host || 'bolt://localhost:7687';
        const dbDisplay = formData.database_name || 'neo4j';
        return `${uri} → ${dbDisplay} (user: ${user})`;
      }
      default:
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
      redis: 6379,
      cassandra: 9042,
      dynamodb: 0,
      elasticsearch: 9200,
      neo4j: 0,
    };

    const defaults: Partial<DatabaseConnection> = {
      database_type: type,
      port: defaultPorts[type] || 5432,
    };

    // Set sensible defaults per type
    if (type === 'dynamodb') {
      defaults.host = 'us-east-1';
      defaults.database_name = '';
    } else if (type === 'redis') {
      defaults.host = 'localhost';
      defaults.database_name = '0';
      defaults.username = '';
    } else if (type === 'elasticsearch') {
      defaults.host = 'localhost';
    } else if (type === 'neo4j') {
      // host holds the full Bolt URI; database_name defaults to "neo4j".
      defaults.host = 'bolt://localhost:7687';
      defaults.username = 'neo4j';
      defaults.database_name = 'neo4j';
      defaults.encrypted = false;
      defaults.read_only = true;
    }

    setFormData((prev) => ({ ...prev, ...defaults }));
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    // Validate required fields
    if (!formData.name || !formData.name.trim()) {
      setTestResult({ success: false, message: 'Connection name is required' });
      return;
    }

    const dbType = formData.database_type;

    // Type-specific validation
    if (dbType === 'dynamodb') {
      if (!formData.host || !formData.host.trim()) {
        setTestResult({ success: false, message: 'AWS Region is required' });
        return;
      }
      if (!formData.username || !formData.username.trim()) {
        setTestResult({ success: false, message: 'Access Key ID is required' });
        return;
      }
      if (!formData.password || !formData.password.trim()) {
        setTestResult({ success: false, message: 'Secret Access Key is required' });
        return;
      }
    } else if (FILE_PATH_TYPES.includes(dbType)) {
      if (!formData.database_name || !formData.database_name.trim()) {
        setTestResult({ success: false, message: 'Database file path is required' });
        return;
      }
    } else if (dbType === 'neo4j') {
      // Neo4j: host carries the full Bolt URI; port lives inside the URI.
      if (!formData.host || !formData.host.trim()) {
        setTestResult({ success: false, message: 'Bolt URI is required (e.g. bolt://localhost:7687)' });
        return;
      }
      if (!formData.username || !formData.username.trim()) {
        setTestResult({ success: false, message: 'Username is required' });
        return;
      }
      if (!formData.password) {
        setTestResult({ success: false, message: 'Password is required' });
        return;
      }
    } else {
      // Standard validation for host/port types
      if (!formData.host || !formData.host.trim()) {
        setTestResult({ success: false, message: 'Host is required' });
        return;
      }
      if (dbType !== 'redis' && (!formData.port || formData.port <= 0)) {
        setTestResult({ success: false, message: 'Valid port number is required' });
        return;
      }
      // Username required for most types, but optional for redis/elasticsearch
      if (!['redis', 'elasticsearch'].includes(dbType)) {
        if (!formData.username || !formData.username.trim()) {
          setTestResult({ success: false, message: 'Username is required' });
          return;
        }
      }
      // Database name required for most, but optional for elasticsearch
      if (!['redis', 'elasticsearch'].includes(dbType)) {
        if (!formData.database_name || !formData.database_name.trim()) {
          setTestResult({ success: false, message: 'Database name is required' });
          return;
        }
      }
    }

    setTesting(true);
    setTestResult(null);

    try {
      const payload: any = {
        name: formData.name.trim(),
        database_type: formData.database_type,
        database_name: (formData.database_name || '').trim(),
      };

      // Include host/port/credentials for non-file-path types
      if (!FILE_PATH_TYPES.includes(dbType)) {
        payload.host = formData.host || 'localhost';
        payload.port = formData.port || 0;
        payload.username = formData.username || '';
        payload.password = formData.password || '';
      }

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);

    // Save write permissions if editing an existing connection
    const connId = connection?.id;
    if (connId && (allowInsert || allowUpdate || allowDelete)) {
      try {
        await dmlAPI.updatePermissions(connId, {
          allow_insert: allowInsert,
          allow_update: allowUpdate,
          allow_delete: allowDelete,
          require_where_clause: requireWhere,
          max_rows_per_operation: maxRows,
          allowed_tables: null,
        });
      } catch {
        // permissions save is best-effort here
      }
    }
    onClose();
  };

  // Render form fields based on database type
  const renderDynamicFields = () => {
    const dbType = formData.database_type;

    // --- File-path types (SQLite, DuckDB) ---
    if (FILE_PATH_TYPES.includes(dbType)) {
      return (
        <div className="space-y-3">
          <label className={labelClass}>Database Target Path *</label>
          <input
            type="text"
            name="database_name"
            value={formData.database_name}
            onChange={handleChange}
            required
            placeholder={dbType === 'duckdb' ? 'e.g., /data/analytics.duckdb' : 'e.g., /data/local.db'}
            className={inputClass}
          />
          {dbType === 'duckdb' && (
            <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-xl text-[11px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              Tip: Use :memory: for an ephemeral in-memory database
            </div>
          )}
        </div>
      );
    }

    // --- DynamoDB (AWS-style: region + access key + secret) ---
    if (dbType === 'dynamodb') {
      return (
        <>
          <div className="space-y-3">
            <label className={labelClass}>AWS Region *</label>
            <input
              type="text"
              name="host"
              value={formData.host}
              onChange={handleChange}
              required
              placeholder="e.g., us-east-1"
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <label className={labelClass}>Access Key ID *</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                placeholder="e.g., AKIAIOSFODNN7EXAMPLE"
                className={inputClass}
              />
            </div>
            <div className="space-y-3">
              <label className={labelClass}>Secret Access Key *</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                placeholder="••••••••"
                className={`${inputClass} font-mono`}
              />
            </div>
          </div>
          <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-xl text-[11px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            AWS credentials are stored locally. Region maps to the DynamoDB endpoint.
          </div>
        </>
      );
    }

    // --- Redis (host + port + optional password + db number) ---
    if (dbType === 'redis') {
      return (
        <>
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1 space-y-3">
              <label className={labelClass}>Host Address *</label>
              <input
                type="text"
                name="host"
                value={formData.host}
                onChange={handleChange}
                required
                placeholder="localhost"
                className={inputClass}
              />
            </div>
            <div className="w-full md:w-32 space-y-3">
              <label className={labelClass}>Port *</label>
              <input
                type="number"
                name="port"
                value={formData.port}
                onChange={handleChange}
                required
                className={`${inputClass} text-center`}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <label className={labelClass}>Password (Optional)</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Leave empty if no auth"
                className={`${inputClass} font-mono`}
              />
            </div>
            <div className="space-y-3">
              <label className={labelClass}>Database Number</label>
              <input
                type="text"
                name="database_name"
                value={formData.database_name}
                onChange={handleChange}
                placeholder="0"
                className={inputClass}
              />
            </div>
          </div>
        </>
      );
    }

    // --- Elasticsearch (host + port + optional auth) ---
    if (dbType === 'elasticsearch') {
      return (
        <>
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1 space-y-3">
              <label className={labelClass}>Host Address *</label>
              <input
                type="text"
                name="host"
                value={formData.host}
                onChange={handleChange}
                required
                placeholder="localhost"
                className={inputClass}
              />
            </div>
            <div className="w-full md:w-32 space-y-3">
              <label className={labelClass}>Port *</label>
              <input
                type="number"
                name="port"
                value={formData.port}
                onChange={handleChange}
                required
                className={`${inputClass} text-center`}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <label className={labelClass}>Username (Optional)</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="Leave empty if no auth"
                className={inputClass}
              />
            </div>
            <div className="space-y-3">
              <label className={labelClass}>Password (Optional)</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Leave empty if no auth"
                className={`${inputClass} font-mono`}
              />
            </div>
          </div>
          <div className="space-y-3">
            <label className={labelClass}>Index Pattern (Optional)</label>
            <input
              type="text"
              name="database_name"
              value={formData.database_name}
              onChange={handleChange}
              placeholder="e.g., logs-* (leave empty for all indices)"
              className={inputClass}
            />
          </div>
        </>
      );
    }

    // --- Neo4j (Bolt URI + database + auth + encryption / read-only toggles) ---
    if (dbType === 'neo4j') {
      return (
        <>
          <div className="space-y-3">
            <label className={labelClass}>Bolt URI *</label>
            <input
              type="text"
              name="host"
              value={formData.host}
              onChange={handleChange}
              required
              placeholder="bolt://localhost:7687  or  neo4j+s://xxx.databases.neo4j.io"
              className={inputClass}
            />
            <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-xl text-[11px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              URI includes the port. ``+s`` schemes auto-enable TLS.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <label className={labelClass}>Username *</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                placeholder="neo4j"
                className={inputClass}
              />
            </div>
            <div className="space-y-3">
              <label className={labelClass}>Password *</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                placeholder="••••••••"
                className={`${inputClass} font-mono`}
              />
            </div>
          </div>

          <div className="space-y-3">
            <label className={labelClass}>Database Name</label>
            <input
              type="text"
              name="database_name"
              value={formData.database_name}
              onChange={handleChange}
              placeholder="neo4j"
              className={inputClass}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex items-center gap-3 p-4 glass-panel bg-white/5 dark:bg-black/10 rounded-2xl cursor-pointer border-white/5">
              <input
                type="checkbox"
                checked={!!formData.encrypted}
                onChange={(e) => {
                  setFormData((prev) => ({ ...prev, encrypted: e.target.checked }));
                  setTestResult(null);
                }}
                className="w-4 h-4 accent-blue-500"
              />
              <div>
                <div className="text-[11px] font-black uppercase tracking-widest text-gray-300">Bolt TLS</div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                  Ignored for neo4j+s / bolt+s URIs
                </div>
              </div>
            </label>
            <label className="flex items-center gap-3 p-4 glass-panel bg-white/5 dark:bg-black/10 rounded-2xl cursor-pointer border-emerald-500/10">
              <input
                type="checkbox"
                checked={formData.read_only !== false}
                onChange={(e) => {
                  setFormData((prev) => ({ ...prev, read_only: e.target.checked }));
                  setTestResult(null);
                }}
                className="w-4 h-4 accent-emerald-500"
              />
              <div>
                <div className="text-[11px] font-black uppercase tracking-widest text-emerald-400">Read-only mode</div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                  Recommended. Driver refuses writes.
                </div>
              </div>
            </label>
          </div>
        </>
      );
    }

    // --- Standard layout (PostgreSQL, MySQL, MSSQL, Oracle, MongoDB, Cassandra) ---
    return (
      <>
        {/* Host and Port */}
        <div className="flex flex-col md:flex-row gap-6">
          <div className="flex-1 space-y-3">
            <label className={labelClass}>
              {dbType === 'cassandra' ? 'Contact Point *' : 'Host Address *'}
            </label>
            <input
              type="text"
              name="host"
              value={formData.host}
              onChange={handleChange}
              required
              placeholder="localhost"
              className={inputClass}
            />
          </div>
          <div className="w-full md:w-32 space-y-3">
            <label className={labelClass}>Port *</label>
            <input
              type="number"
              name="port"
              value={formData.port}
              onChange={handleChange}
              required
              className={`${inputClass} text-center`}
            />
          </div>
        </div>

        {/* Database Name / Service Name / Keyspace */}
        <div className="space-y-3">
          <label className={labelClass}>
            {dbType === 'oracle' ? 'Service Name *'
              : dbType === 'cassandra' ? 'Keyspace *'
              : dbType === 'mongodb' ? 'Database Name *'
              : 'Database Schema Name *'}
          </label>
          <input
            type="text"
            name="database_name"
            value={formData.database_name}
            onChange={handleChange}
            required
            placeholder={
              dbType === 'oracle' ? 'e.g., ORCL or XEPDB1'
              : dbType === 'cassandra' ? 'e.g., my_keyspace'
              : dbType === 'mongodb' ? 'e.g., my_database'
              : 'e.g., app_production'
            }
            className={inputClass}
          />
          {dbType === 'oracle' && (
            <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-xl text-[11px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              Tip: Use the Oracle service name (e.g., ORCL, XEPDB1) — not the SID
            </div>
          )}
        </div>

        {/* Username and Password */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <label className={labelClass}>Authority Username *</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="e.g., db_admin"
              className={inputClass}
            />
          </div>
          <div className="space-y-3">
            <label className={labelClass}>Authority Secret *</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="••••••••"
              className={`${inputClass} font-mono`}
            />
          </div>
        </div>
      </>
    );
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
            <label className={labelClass}>Connection Identifier *</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="e.g., Production Analytics"
              className={inputClass}
            />
          </div>

          {/* Database Type */}
          <div className="space-y-4">
            <label className={labelClass}>Select Protocol *</label>
            <div className="flex flex-wrap gap-2.5">
              {['postgresql', 'mysql', 'sqlite', 'mssql', 'oracle', 'mongodb', 'duckdb', 'redis', 'cassandra', 'dynamodb', 'elasticsearch', 'neo4j'].map((type) => (
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
          {renderDynamicFields()}

          {/* Write Permissions */}
          <div className="border-t border-white/5 pt-8">
            <div className="flex items-center gap-3 mb-6">
              <Shield className="w-5 h-5 text-emerald-500" />
              <label className={labelClass}>Write Permissions (Edit Mode)</label>
            </div>
            {!connection?.id && (
              <p className="text-[11px] text-amber-500 font-bold mb-4">Save the connection first, then edit it to configure write permissions.</p>
            )}
            <div className={`space-y-3 ${!connection?.id ? 'opacity-40 pointer-events-none' : ''}`}>
              {[
                { label: 'Allow Insert', desc: 'Add new rows', checked: allowInsert, onChange: setAllowInsert },
                { label: 'Allow Update', desc: 'Edit existing rows', checked: allowUpdate, onChange: setAllowUpdate },
                { label: 'Allow Delete', desc: 'Remove rows', checked: allowDelete, onChange: setAllowDelete },
              ].map(({ label, desc, checked, onChange }) => (
                <div key={label} className="flex items-center justify-between p-4 glass-panel rounded-xl">
                  <div>
                    <span className="text-sm font-bold text-gray-900 dark:text-white">{label}</span>
                    <p className="text-[11px] text-gray-500">{desc}</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={checked}
                    onClick={() => onChange(!checked)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer ${checked ? 'bg-emerald-600' : 'bg-gray-600'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              ))}
              {(allowInsert || allowUpdate || allowDelete) && (
                <div className="flex items-center justify-between p-4 glass-panel rounded-xl mt-3">
                  <div>
                    <span className="text-sm font-bold text-gray-900 dark:text-white">Require WHERE clause</span>
                    <p className="text-[11px] text-gray-500">Prevent unscoped updates/deletes</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={requireWhere}
                    onClick={() => setRequireWhere(!requireWhere)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer ${requireWhere ? 'bg-emerald-600' : 'bg-gray-600'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${requireWhere ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Connection String Preview */}
          <div className="border-t border-white/5 pt-8">
            <div className="flex items-center justify-between mb-4">
              <label className={labelClass}>Connection String Protocol</label>
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
