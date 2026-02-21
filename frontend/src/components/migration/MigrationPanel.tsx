import { useState, useEffect } from 'react';
import { Loader2, GitCompare, FolderOpen, ListOrdered, FileCode, Database } from 'lucide-react';
import { migrationAPI } from '../../services/migrationApi';
import { SchemaDiffPanel } from './SchemaDiffPanel';
import { MigrationPlanPanel } from './MigrationPlanPanel';
import { ScriptGeneratorPanel } from './ScriptGeneratorPanel';
import { DataMigrationPanel } from './DataMigrationPanel';
import type { MigrationProjectSummary, MigrationProjectDetail } from '../../types/migration';

type TabId = 'compare' | 'projects' | 'plan' | 'scripts' | 'data';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'compare', label: 'Compare', icon: <GitCompare className="w-3.5 h-3.5" /> },
  { id: 'projects', label: 'Projects', icon: <FolderOpen className="w-3.5 h-3.5" /> },
  { id: 'plan', label: 'Plan', icon: <ListOrdered className="w-3.5 h-3.5" /> },
  { id: 'scripts', label: 'Scripts', icon: <FileCode className="w-3.5 h-3.5" /> },
  { id: 'data', label: 'Data', icon: <Database className="w-3.5 h-3.5" /> },
];

const RISK_COLORS: Record<string, string> = {
  none: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  critical: 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-200',
};

export function MigrationPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('compare');
  const [projects, setProjects] = useState<MigrationProjectSummary[]>([]);
  const [selectedProject, setSelectedProject] = useState<MigrationProjectDetail | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(false);

  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      const data = await migrationAPI.listProjects();
      setProjects(data);
    } catch {
      // silently handle
    } finally {
      setLoadingProjects(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleProjectCreated = (projectId: number) => {
    loadProjects();
    selectProject(projectId);
  };

  const selectProject = async (projectId: number) => {
    try {
      const detail = await migrationAPI.getProject(projectId);
      setSelectedProject(detail);
    } catch {
      // handle error
    }
  };

  const handleDeleteProject = async (id: number) => {
    try {
      await migrationAPI.deleteProject(id);
      if (selectedProject?.id === id) setSelectedProject(null);
      loadProjects();
    } catch {
      // handle error
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Tab strip */}
      <div className="flex-shrink-0 px-4 pt-4 pb-2">
        <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wide transition-all duration-300 ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Active project indicator */}
        {selectedProject && (
          <div className="mt-2 px-3 py-2 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg flex items-center gap-2">
            <FolderOpen className="w-3.5 h-3.5 text-indigo-500" />
            <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300">
              {selectedProject.name}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK_COLORS[selectedProject.overall_risk || 'none']}`}>
              {selectedProject.overall_risk || 'N/A'}
            </span>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">
              {selectedProject.status}
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-auto p-4">
        {activeTab === 'compare' && (
          <SchemaDiffPanel onProjectCreated={handleProjectCreated} />
        )}

        {activeTab === 'projects' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                Migration Projects
              </h3>
              <button
                onClick={loadProjects}
                disabled={loadingProjects}
                className="px-3 py-1.5 text-xs font-bold rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              >
                {loadingProjects ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Refresh'}
              </button>
            </div>

            {projects.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">
                No migration projects yet. Use the Compare tab to create one.
              </p>
            ) : (
              projects.map((p) => (
                <div
                  key={p.id}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    selectedProject?.id === p.id
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                      : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-indigo-300 dark:hover:border-indigo-700'
                  }`}
                  onClick={() => selectProject(p.id)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-gray-900 dark:text-white">{p.name}</h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {p.source_connection_name || `ID ${p.source_connection_id}`} →{' '}
                        {p.target_connection_name || `ID ${p.target_connection_id}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK_COLORS[p.overall_risk || 'none']}`}>
                        {p.overall_risk || 'N/A'}
                      </span>
                      <span className="text-[10px] text-gray-400 uppercase font-bold">{p.status}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteProject(p.id); }}
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                        title="Delete project"
                      >
                        &times;
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'plan' && (
          selectedProject ? (
            <MigrationPlanPanel project={selectedProject} onRefresh={() => selectProject(selectedProject.id)} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">
              Select a project from the Projects tab first.
            </p>
          )
        )}

        {activeTab === 'scripts' && (
          selectedProject ? (
            <ScriptGeneratorPanel project={selectedProject} onRefresh={() => selectProject(selectedProject.id)} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">
              Select a project from the Projects tab first.
            </p>
          )
        )}

        {activeTab === 'data' && (
          selectedProject ? (
            <DataMigrationPanel project={selectedProject} onRefresh={() => selectProject(selectedProject.id)} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">
              Select a project from the Projects tab first.
            </p>
          )
        )}
      </div>
    </div>
  );
}
