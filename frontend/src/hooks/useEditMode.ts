// Edit mode state management — Phase 18
import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dmlAPI } from '../services/dmlApi';
import type { WritePermission } from '../types/dml';

const NOSQL_TYPES = new Set([
  'mongodb',
  'redis',
  'cassandra',
  'dynamodb',
  'elasticsearch',
]);

interface UseEditModeOptions {
  connectionId: number | null;
  databaseType: string | null;
}

export function useEditMode({ connectionId, databaseType }: UseEditModeOptions) {
  const [isEditMode, setIsEditMode] = useState(false);

  const isNoSQL = databaseType ? NOSQL_TYPES.has(databaseType) : false;

  const {
    data: permissions,
    isLoading: permissionsLoading,
  } = useQuery<WritePermission>({
    queryKey: ['dml-permissions', connectionId],
    queryFn: () => dmlAPI.getPermissions(connectionId!),
    enabled: connectionId !== null && !isNoSQL,
    staleTime: 30_000,
  });

  const canEdit = useMemo(() => {
    if (!connectionId || isNoSQL || !permissions) return false;
    return (
      permissions.write_enabled &&
      (permissions.allow_insert ||
        permissions.allow_update ||
        permissions.allow_delete)
    );
  }, [connectionId, isNoSQL, permissions]);

  const toggleEditMode = useCallback(() => {
    if (canEdit) {
      setIsEditMode((prev) => !prev);
    }
  }, [canEdit]);

  const exitEditMode = useCallback(() => {
    setIsEditMode(false);
  }, []);

  const disabledReason = useMemo((): string | null => {
    if (!connectionId) return 'No active connection';
    if (isNoSQL) return 'Edit mode is not available for NoSQL databases';
    if (permissionsLoading) return 'Loading permissions...';
    if (!permissions?.write_enabled) return 'Write permissions not configured for this connection';
    if (
      !permissions.allow_insert &&
      !permissions.allow_update &&
      !permissions.allow_delete
    )
      return 'No write operations are allowed on this connection';
    return null;
  }, [connectionId, isNoSQL, permissionsLoading, permissions]);

  return {
    isEditMode,
    canEdit,
    permissions,
    permissionsLoading,
    toggleEditMode,
    exitEditMode,
    disabledReason,
    isNoSQL,
  };
}
