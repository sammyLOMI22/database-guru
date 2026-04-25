Implementation Plan — UI Integration Gaps                                                                                                            
                                                                                                                                                       
  1. Audit Log Viewer (Admin)                                                                                                                          
                                                                                                                                                       
  Backend (src/api/endpoints/audit.py)                                                                                                                 
  - Verify GET /api/audit/logs exists with filters: user_id, action, resource_type, start_date, end_date, limit, offset. Add if missing, gated by      
  require_admin.                                                                                                                                       
  - Add GET /api/audit/actions returning distinct action types for filter dropdown.
                                                                                                                                                       
  Frontend                                                                                                                                             
  - New frontend/src/components/admin/AuditLogViewer.tsx — paginated table (timestamp, user, action, resource, IP, status), filter bar, JSON details
  drawer per row.                                                                                                                                      
  - New frontend/src/services/auditApi.ts — thin axios wrapper.
  - App.tsx: add 'admin' to activeTab union; render only when user?.role === 'admin'.                                                                  
  - Sidebar.tsx: conditional "Admin" entry.                                          
                                                                                                                                                       
  2. User Management (Admin)                                                                                                                           
                                                                                                                                                       
  Backend (src/api/endpoints/auth.py or new users.py)                                                                                                  
  - GET /api/admin/users (list w/ pagination)
  - PATCH /api/admin/users/{id} (role, is_active)                                                                                                      
  - POST /api/admin/users/{id}/reset-password (returns temp password or triggers reset flow)
  - DELETE /api/admin/users/{id} (soft-delete via is_active=False)                                                                                     
  - All gated by require_admin; each action writes to AuditLog.                                                                                        
                                                                                                                                                       
  Frontend                                                                                                                                             
  - New frontend/src/components/admin/UserManagement.tsx — table with inline role toggle, disable button, reset-password modal.                        
  - New frontend/src/components/admin/CreateUserModal.tsx.                                                                                             
  - Lives under same "Admin" tab as audit viewer (sub-tabs: Users / Audit).
                                                                                                                                                       
  3. Observability Surfacing (Phase 24)                                                                                                                
                                                                                                                                                       
  Backend — no changes; request_id already in response headers via middleware.                                                                         
                                                                                                                                                       
  Frontend                                                                                                                                             
  - Header.tsx: small "Last request: <short-id>" badge, click → copies full request_id + trace_id to clipboard. Read from response header in axios
  interceptor, store in zustand/context.                                                                                                               
  - frontend/src/services/api.ts: response interceptor captures x-request-id / traceparent headers into a useLastRequest store.
  - SettingsPanel.tsx: new "Observability" section with deep-links (configurable URLs from /api/settings):                                             
    - METRICS_URL → Prometheus /metrics                                                                                                                
    - JAEGER_URL → Jaeger UI                                                                                                                           
    - GRAFANA_URL → Grafana dashboard                                                                                                                  
  - settings.py: add optional JAEGER_UI_URL, GRAFANA_URL, METRICS_PUBLIC_URL env vars; expose via public settings endpoint.                            
  - Promote ObservabilityDemo from ?demo=true to a "Health" sub-tab inside Settings (admin-only).                                                      
                                                                                                                                                       
  Shared Plumbing                                                                                                                                      
                                                                                                                                                       
  - useAuth hook: ensure user.role is exposed (may already be).                                                                                        
  - New frontend/src/components/common/RequireAdmin.tsx guard component.                                                                               
  - Add frontend/src/services/adminApi.ts for users + audit endpoints.                                                                                 
                                                                                                                                                       
  Test Coverage                                                                                                                                        
                                                                                                                                                       
  - tests/api/test_audit_endpoints.py — admin filter/pagination, non-admin 403.                                                                        
  - tests/api/test_admin_users.py — role change, disable, reset-password, audit-log side-effect assertion.
  - Frontend: vitest for AuditLogViewer filter state + useLastRequest interceptor.                                                                     
                                                                                                                                                       
  Suggested Order (small, shippable PRs)                                                                                                               
                                                                                                                                                       
  1. PR 1 — Trace-ID in header + axios interceptor (~½ day, lowest risk).                                                                              
  2. PR 2 — Audit log viewer + admin tab scaffolding (~1 day).
  3. PR 3 — Observability deep-links in Settings (~½ day).                                                                                             
  4. PR 4 — User management CRUD (~1.5 days, biggest scope).
  Implementation Plan — UI Integration Gaps                                                                                                            
                                                                                                                                                       
  1. Audit Log Viewer (Admin)                                                                                                                          
                                                                                                                                                       
  Backend (src/api/endpoints/audit.py)                                                                                                                 
  - Verify GET /api/audit/logs exists with filters: user_id, action, resource_type, start_date, end_date, limit, offset. Add if missing, gated by      
  require_admin.                                                                                                           
  - Add GET /api/audit/actions returning distinct action types for filter dropdown.
                                                                                                                                                       
  Frontend                                                                                                                                             
  - New frontend/src/components/admin/AuditLogViewer.tsx — paginated table (timestamp, user, action, resource, IP, status), filter bar, JSON details
  drawer per row.                                                                                                                                      
  - New frontend/src/services/auditApi.ts — thin axios wrapper.
  - App.tsx: add 'admin' to activeTab union; render only when user?.role === 'admin'.                                                                  
  - Sidebar.tsx: conditional "Admin" entry.                                          
                                                                                                                                                       
  2. User Management (Admin)                                                                                                                           
                                                                                                                                                       
  Backend (src/api/endpoints/auth.py or new users.py)                                                                                                  
  - GET /api/admin/users (list w/ pagination)
  - PATCH /api/admin/users/{id} (role, is_active)                                                                                                      
  - POST /api/admin/users/{id}/reset-password (returns temp password or triggers reset flow)
  - DELETE /api/admin/users/{id} (soft-delete via is_active=False)                                                                                     
  - All gated by require_admin; each action writes to AuditLog.                                                                                        
                                                                                                                                                       
  Frontend                                                                                                                                             
  - New frontend/src/components/admin/UserManagement.tsx — table with inline role toggle, disable button, reset-password modal.                        
  - New frontend/src/components/admin/CreateUserModal.tsx.                                                                                             
  - Lives under same "Admin" tab as audit viewer (sub-tabs: Users / Audit).
                                                                                                                                                       
  3. Observability Surfacing (Phase 24)                                                                                                                
                                                                                                                                                       
  Backend — no changes; request_id already in response headers via middleware.                                                                         
                                                                                                                                                       
  Frontend                                                                                                                                             
  - Header.tsx: small "Last request: <short-id>" badge, click → copies full request_id + trace_id to clipboard. Read from response header in axios
  interceptor, store in zustand/context.                                                                                                               
  - frontend/src/services/api.ts: response interceptor captures x-request-id / traceparent headers into a useLastRequest store.
  - SettingsPanel.tsx: new "Observability" section with deep-links (configurable URLs from /api/settings):                                             
    - METRICS_URL → Prometheus /metrics                                                                                                                
    - JAEGER_URL → Jaeger UI                                                                                                                           
    - GRAFANA_URL → Grafana dashboard                                                                                                                  
  - settings.py: add optional JAEGER_UI_URL, GRAFANA_URL, METRICS_PUBLIC_URL env vars; expose via public settings endpoint.                            
  - Promote ObservabilityDemo from ?demo=true to a "Health" sub-tab inside Settings (admin-only).                                                      
                                                                                                                                                       
  Shared Plumbing                                                                                                                                      
                                                                                                                                                       
  - useAuth hook: ensure user.role is exposed (may already be).                                                                                        
  - New frontend/src/components/common/RequireAdmin.tsx guard component.                                                                               
  - Add frontend/src/services/adminApi.ts for users + audit endpoints.                                                                                 
                                                                                                                                                       
  Test Coverage                                                                                                                                        
                                                                                                                                                       
  - tests/api/test_audit_endpoints.py — admin filter/pagination, non-admin 403.                                                                        
  - tests/api/test_admin_users.py — role change, disable, reset-password, audit-log side-effect assertion.
  - Frontend: vitest for AuditLogViewer filter state + useLastRequest interceptor.                                                                     
                                                                                                                                                       
  Suggested Order (small, shippable PRs)                                                                                                               
                                                                                                                                                       
  1. PR 1 — Trace-ID in header + axios interceptor (~½ day, lowest risk).                                                                              
  2. PR 2 — Audit log viewer + admin tab scaffolding (~1 day).
  3. PR 3 — Observability deep-links in Settings (~½ day).                                                                                             
  4. PR 4 — User management CRUD (~1.5 days, biggest scope).
   Backend (src/api/endpoints/auth.py or new users.py)
  - GET /api/admin/users (list w/ pagination)
  - PATCH /api/admin/users/{id} (role, is_active)
  - POST /api/admin/users/{id}/reset-password (returns temp password or triggers reset flow)
  - DELETE /api/admin/users/{id} (soft-delete via is_active=False)
  - All gated by require_admin; each action writes to AuditLog.

  Frontend
  - New frontend/src/components/admin/UserManagement.tsx — table with inline role toggle, disable button, reset-password modal.
  - New frontend/src/components/admin/CreateUserModal.tsx.
  - Lives under same "Admin" tab as audit viewer (sub-tabs: Users / Audit).

  3. Observability Surfacing (Phase 24)

  Backend — no changes; request_id already in response headers via middleware.

  Frontend
  - Header.tsx: small "Last request: <short-id>" badge, click → copies full request_id + trace_id to clipboard. Read from response header in axios
  interceptor, store in zustand/context.
  - frontend/src/services/api.ts: response interceptor captures x-request-id / traceparent headers into a useLastRequest store.
  - SettingsPanel.tsx: new "Observability" section with deep-links (configurable URLs from /api/settings):
    - METRICS_URL → Prometheus /metrics
    - JAEGER_URL → Jaeger UI
    - GRAFANA_URL → Grafana dashboard
  - settings.py: add optional JAEGER_UI_URL, GRAFANA_URL, METRICS_PUBLIC_URL env vars; expose via public settings endpoint.
  - Promote ObservabilityDemo from ?demo=true to a "Health" sub-tab inside Settings (admin-only).

  Shared Plumbing

  - useAuth hook: ensure user.role is exposed (may already be).
  - New frontend/src/components/common/RequireAdmin.tsx guard component.
  - Add frontend/src/services/adminApi.ts for users + audit endpoints.

  Test Coverage

  - tests/api/test_audit_endpoints.py — admin filter/pagination, non-admin 403.
  - tests/api/test_admin_users.py — role change, disable, reset-password, audit-log side-effect assertion.
  - Frontend: vitest for AuditLogViewer filter state + useLastRequest interceptor.

  Suggested Order (small, shippable PRs)

  1. PR 1 — Trace-ID in header + axios interceptor (~½ day, lowest risk).
  2. PR 2 — Audit log viewer + admin tab scaffolding (~1 day).
  3. PR 3 — Observability deep-links in Settings (~½ day).
  4. PR 4 — User management CRUD (~1.5 days, biggest scope).