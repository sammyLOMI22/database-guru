// DML preview & execution mutations — Phase 18
import { useMutation } from '@tanstack/react-query';
import { dmlAPI } from '../services/dmlApi';
import type {
  DMLPreviewRequest,
  DMLPreviewResponse,
  DMLExecuteRequest,
  DMLExecuteResponse,
} from '../types/dml';

export function useDMLPreview() {
  return useMutation<DMLPreviewResponse, Error, DMLPreviewRequest>({
    mutationFn: (request) => dmlAPI.preview(request),
  });
}

export function useDMLExecute() {
  return useMutation<DMLExecuteResponse, Error, DMLExecuteRequest>({
    mutationFn: (request) => dmlAPI.execute(request),
  });
}
