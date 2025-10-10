import { useState } from 'react';
import { X } from 'lucide-react';

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

  if (!isOpen) return null;

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
        message: formData.database_type === 'sqlite'
          ? 'Database file path is required'
          : 'Database name is required',
      });
      return;
    }

    // For non-SQLite, validate host and port
    if (formData.database_type !== 'sqlite') {
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

      // Only include host/port/username/password for non-SQLite databases
      if (formData.database_type !== 'sqlite') {
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">
            {connection ? 'Edit Database Connection' : 'Add Database Connection'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Connection Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Connection Name *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="My Production Database"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Database Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Database Type *
            </label>
            <div className="grid grid-cols-4 gap-3">
              {['postgresql', 'mysql', 'sqlite', 'mongodb'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleDatabaseTypeChange(type)}
                  className={`px-4 py-2 rounded-lg border-2 transition-all ${
                    formData.database_type === type
                      ? 'border-primary-500 bg-primary-50 text-primary-700 font-medium'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* SQLite File Path (if SQLite) */}
          {formData.database_type === 'sqlite' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Database File Path *
              </label>
              <input
                type="text"
                name="database_name"
                value={formData.database_name}
                onChange={handleChange}
                required
                placeholder="/path/to/database.db"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          ) : (
            <>
              {/* Host and Port */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Host *</label>
                  <input
                    type="text"
                    name="host"
                    value={formData.host}
                    onChange={handleChange}
                    required
                    placeholder="localhost"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Port *</label>
                  <input
                    type="number"
                    name="port"
                    value={formData.port}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Database Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Database Name *
                </label>
                <input
                  type="text"
                  name="database_name"
                  value={formData.database_name}
                  onChange={handleChange}
                  required
                  placeholder="myapp_production"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>

              {/* Username and Password */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Username *
                  </label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    required
                    placeholder="dbuser"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Password *
                  </label>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    placeholder="••••••••"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              </div>
            </>
          )}

          {/* Test Result */}
          {testResult && (
            <div
              className={`p-4 rounded-lg ${
                testResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
              }`}
            >
              <p className="font-medium">{testResult.message}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <div className="flex-1" />
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Save Connection
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
