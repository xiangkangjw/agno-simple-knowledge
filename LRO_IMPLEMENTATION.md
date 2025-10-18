# Long Running Operations (LRO) Implementation

## Overview

The indexer timeout issue has been resolved by implementing a **Long Running Operations (LRO)** pattern with SQLite persistence. This allows large document indexing operations to run asynchronously without timing out.

## Problem Statement

When refreshing the index with many documents (especially large PDFs), the HTTP request would timeout because:
1. The blocking indexing operation ran on the main event loop
2. FastAPI had a request timeout (typically 60-300 seconds)
3. Large document sets took longer than the timeout window

## Solution Architecture

### 1. **OperationManager** (`python-backend/core/operation_manager.py`)
- **SQLite-based** tracking of all operations
- **Async-safe** using `asyncio.to_thread()` for all DB operations
- Supports full lifecycle: create → start → progress → complete/fail/cancel
- Automatic cleanup of old operations (configurable retention period)

**Database Schema:**
```sql
CREATE TABLE operations (
    id TEXT PRIMARY KEY,
    operation_type TEXT,
    status TEXT,
    created_at REAL,
    updated_at REAL,
    started_at REAL,
    completed_at REAL,
    total_items INTEGER,
    processed_items INTEGER,
    failed_items INTEGER,
    current_item TEXT,
    result TEXT,
    error TEXT
)
```

### 2. **DocumentIndexingService Refactor**
- `refresh_index()` now returns immediately with an `operation_id`
- Actual indexing runs in a background `asyncio.Task`
- Progress tracked in SQLite as processing continues
- Result stored upon completion

**Flow:**
```
POST /api/documents/refresh
  ↓
return {"operation_id": "refresh-abc123", "status": "pending"}
  ↓
Background task starts (indexed in thread pool)
  ↓
GET /api/operations/refresh-abc123 (poll for progress)
  ↓
Returns {"status": "running", "processed_items": 25, "total_items": 100}
  ↓
When complete: {"status": "completed", "result": {...}}
```

### 3. **New API Endpoints** (`python-backend/api/routes/operations.py`)

#### Get Operation Status
```
GET /api/operations/{operation_id}
Response:
{
  "success": true,
  "operation": {
    "id": "refresh-abc123",
    "operation_type": "refresh_index",
    "status": "running",
    "created_at": 1697641200.123,
    "started_at": 1697641205.456,
    "total_items": 100,
    "processed_items": 45,
    "current_item": "document_45.pdf"
  }
}
```

#### List Recent Operations
```
GET /api/operations?limit=50&status=completed
Response:
{
  "success": true,
  "operations": [...],
  "count": 15
}
```

#### Cancel Operation
```
POST /api/operations/{operation_id}/cancel
Response:
{
  "success": true,
  "message": "Operation refresh-abc123 cancelled"
}
```

### 4. **Configuration** (`config.yaml`)
```yaml
operations:
  database_file: "tmp/operations.db"
  cleanup_after_hours: 24
  max_timeout_seconds: 3600
```

## Files Changed

### New Files
- `python-backend/core/operation_manager.py` - Core LRO implementation
- `python-backend/api/routes/operations.py` - API endpoints
- `test_lro.py` - Comprehensive test suite

### Modified Files
- `config.yaml` - Added operations section
- `python-backend/core/document_service.py` - Refactored for LRO
- `python-backend/core/knowledge_system.py` - Integrated OperationManager
- `python-backend/api/routes/documents.py` - Updated endpoints
- `python-backend/main.py` - Added operations router

## Key Features

✅ **No More Timeouts** - Operations run in background indefinitely
✅ **Progress Tracking** - Real-time updates via polling
✅ **Persistent** - All operations stored in SQLite
✅ **Cancellable** - Users can cancel running operations
✅ **Auto-cleanup** - Old operations automatically deleted
✅ **Async-safe** - Thread pool used for blocking operations
✅ **Error Handling** - Detailed error messages on failure

## Usage Examples

### Frontend (React/TypeScript)

```typescript
// Start refresh
const response = await fetch('/api/documents/refresh', { method: 'POST' });
const { operation_id } = await response.json();

// Poll for progress
const pollInterval = setInterval(async () => {
  const statusResponse = await fetch(`/api/operations/${operation_id}`);
  const { operation } = await statusResponse.json();

  if (operation.status === 'completed') {
    clearInterval(pollInterval);
    console.log('Done!', operation.result);
  } else if (operation.status === 'failed') {
    clearInterval(pollInterval);
    console.error('Failed:', operation.error);
  } else {
    // Update UI with progress
    console.log(`Progress: ${operation.processed_items}/${operation.total_items}`);
  }
}, 2000); // Poll every 2 seconds
```

### Python Backend

```python
# The operation is created and run automatically via the API
# But if you need to create one directly:

operation_id = await operation_manager.create_operation('refresh_index', total_items=100)
await operation_manager.start_operation(operation_id)

# Simulate progress
for i in range(1, 101):
    await operation_manager.update_progress(operation_id, processed_items=i)

# Complete it
await operation_manager.complete_operation(operation_id, {'success': True})
```

## Testing

Run the test suite:
```bash
python3 test_lro.py
```

Tests cover:
- ✓ Operation creation
- ✓ Status retrieval
- ✓ Progress updates
- ✓ Completion with results
- ✓ Failure handling
- ✓ Cancellation
- ✓ Cleanup
- ✓ DocumentIndexingService integration

## Benefits

1. **User Experience** - No "spinning wheel" timeouts; users see real progress
2. **Scalability** - Can handle large document sets without API timeouts
3. **Reliability** - Persistent tracking survives app restarts
4. **Debugging** - Full audit trail of all operations
5. **Control** - Users can cancel long-running operations

## Next Steps (Optional Enhancements)

- [ ] Add WebSocket support for real-time progress (vs polling)
- [ ] Add batch operation support (queue multiple refreshes)
- [ ] Add operation history/analytics dashboard
- [ ] Add per-operation timeout limits
- [ ] Add operation priority queue
- [ ] Add progress callbacks with email/notifications
