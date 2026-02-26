// Phase 20: Migration Toolkit API
import api from './api';
import type {
  SchemaDiffResponse,
  MigrationProjectSummary,
  MigrationProjectDetail,
  MigrationPlanResponse,
  GeneratedScriptsResponse,
  DataMigrationPlanResponse,
  BackupScriptsResponse,
  SchemaObjectFlags,
} from '../types/migration';

export const migrationAPI = {
  // Schema Diff (20.1)
  async compareDatabases(
    sourceId: number,
    targetId: number,
    save = false,
    name?: string,
    flags?: SchemaObjectFlags,
  ): Promise<SchemaDiffResponse> {
    const { data } = await api.post<SchemaDiffResponse>('/api/migration/diff', {
      source_connection_id: sourceId,
      target_connection_id: targetId,
      save,
      name,
      ...flags,
    });
    return data;
  },

  // Projects CRUD (20.1)
  async listProjects(): Promise<MigrationProjectSummary[]> {
    const { data } = await api.get<MigrationProjectSummary[]>('/api/migration/projects');
    return data;
  },

  async getProject(id: number): Promise<MigrationProjectDetail> {
    const { data } = await api.get<MigrationProjectDetail>(`/api/migration/projects/${id}`);
    return data;
  },

  async deleteProject(id: number): Promise<void> {
    await api.delete(`/api/migration/projects/${id}`);
  },

  // Migration Planner (20.2)
  async generatePlan(projectId: number): Promise<MigrationPlanResponse> {
    const { data } = await api.post<MigrationPlanResponse>(`/api/migration/projects/${projectId}/plan`);
    return data;
  },

  async getPlan(projectId: number): Promise<MigrationPlanResponse> {
    const { data } = await api.get<MigrationPlanResponse>(`/api/migration/projects/${projectId}/plan`);
    return data;
  },

  // Script Generator (20.3)
  async generateScripts(
    projectId: number,
    targetDialect: string,
    flags?: SchemaObjectFlags,
  ): Promise<GeneratedScriptsResponse> {
    const { data } = await api.post<GeneratedScriptsResponse>(
      `/api/migration/projects/${projectId}/scripts`,
      { target_dialect: targetDialect, ...flags },
    );
    return data;
  },

  async getScripts(projectId: number): Promise<GeneratedScriptsResponse> {
    const { data } = await api.get<GeneratedScriptsResponse>(`/api/migration/projects/${projectId}/scripts`);
    return data;
  },

  async downloadScript(projectId: number, filename: string): Promise<string> {
    const { data } = await api.get<string>(`/api/migration/projects/${projectId}/scripts/${filename}`, {
      responseType: 'text' as any,
    });
    return data;
  },

  // Data Migration (20.4)
  async generateDataMigration(projectId: number, batchSize = 1000): Promise<DataMigrationPlanResponse> {
    const { data } = await api.post<DataMigrationPlanResponse>(
      `/api/migration/projects/${projectId}/data-migration?batch_size=${batchSize}`,
    );
    return data;
  },

  async getDataMigration(projectId: number): Promise<DataMigrationPlanResponse> {
    const { data } = await api.get<DataMigrationPlanResponse>(`/api/migration/projects/${projectId}/data-migration`);
    return data;
  },

  // Single-database Backup / Restore Scripts
  async generateBackupScripts(
    connectionId: number,
    dialect?: string,
    flags?: SchemaObjectFlags,
  ): Promise<BackupScriptsResponse> {
    const { data } = await api.post<BackupScriptsResponse>('/api/migration/backup', {
      connection_id: connectionId,
      dialect: dialect || null,
      ...flags,
    });
    return data;
  },
};
