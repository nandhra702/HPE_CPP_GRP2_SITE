# Proctoring Debug Mode Guide

## Overview
The proctoring system now supports a debug mode that allows you to disable backend connections while still testing the frontend proctoring features.

## How to Enable/Disable Backend Connection

### Using the Debug Flag

The debug option is controlled in `judge/debug.py`:

```python
# Proctoring debug settings
PROCTORING_DEBUG = True  # Enable proctoring debug features
PROCTORING_DISABLE_BACKEND = True  # Disable backend connection (run in local-only mode)
```

### Configuration Options

1. **Enable Backend (Normal Mode)**
   ```python
   PROCTORING_DISABLE_BACKEND = False
   ```
   - Connects to backend server at `http://127.0.0.1:8001`
   - Sends session data, video clips, and tab switch events
   - Requires backend server to be running

2. **Disable Backend (Debug Mode)**
   ```python
   PROCTORING_DISABLE_BACKEND = True
   ```
   - Runs in local-only mode
   - No backend connections attempted
   - All proctoring security features still work (fullscreen, camera, tab detection)
   - Data is logged locally but not uploaded
   - Useful for frontend testing without backend

## What Changes When Backend is Disabled

### Skipped Operations
When `PROCTORING_DISABLE_BACKEND = True`:

1. **Session Management**
   - No `/start-session` API call
   - Generates local session ID: `local_<timestamp>_<random>`
   - No `/stop-session` API call
   - No `/check-session` API call

2. **WebSocket Connection**
   - WebSocket initialization is skipped
   - No real-time monitoring connection
   - Tab switch events logged locally only

3. **Video Upload**
   - Violation videos still recorded locally
   - Video upload to `/upload-clip` is skipped
   - Chunks are logged but not sent to server

### Still Active Features
Even with backend disabled, these features remain active:

1. **Fullscreen Enforcement**
   - Fullscreen mode still required
   - Exit attempts still blocked
   - Modal warnings still shown

2. **Camera Monitoring**
   - Camera access still required
   - Video stream still captured
   - Local recording still works

3. **Tab Switch Detection**
   - Tab switches still detected and counted
   - Time outside still tracked
   - Console logging still active

4. **Security Locks**
   - Keyboard shortcuts still blocked
   - Right-click context menu still disabled
   - Copy/paste still prevented
   - F11 still blocked

## Console Messages

### Backend Enabled
```
[DEBUG] Backend connection ENABLED
[DEBUG] Sending session start request with: {...}
[DEBUG] Initializing WebSocket to: ws://127.0.0.1:8001/ws?session_id=...
```

### Backend Disabled
```
[DEBUG] Backend connection DISABLED by debug settings
[DEBUG] Backend disabled - using local-only mode
[DEBUG] Backend disabled - skipping session check
[DEBUG] Backend disabled or running in local-only mode - skipping WebSocket connection
[DEBUG] Backend disabled - skipping tab switch update
[DEBUG] Backend disabled - skipping violation video upload
```

## Use Cases

### Testing Without Backend
```python
# In judge/debug.py
PROCTORING_DISABLE_BACKEND = True
```
- Test frontend UI flow
- Test camera and fullscreen permissions
- Test security locks and restrictions
- No need to run backend server

### Full Integration Testing
```python
# In judge/debug.py
PROCTORING_DISABLE_BACKEND = False
```
- Test complete system
- Verify backend communication
- Test data persistence
- Requires backend server running

## Master Debug Switch

You can disable all debug features at once:

```python
# In judge/debug.py
MASTER_DEBUG_ENABLED = False  # Disables all debug features including backend disable
```

This will:
- Force backend connection even if `PROCTORING_DISABLE_BACKEND = True`
- Disable other debug features like contest rejoin

## Implementation Details

### Backend Check Flow

1. **Template receives flag** from Django view:
   ```javascript
   window.dmojData = {
       userId: ...,
       username: ...,
       contestKey: ...,
       contestName: ...,
       disableBackend: true/false  // From get_proctoring_disable_backend()
   }
   ```

2. **JavaScript checks flag** before any backend operation:
   ```javascript
   const DISABLE_BACKEND = window.dmojData && window.dmojData.disableBackend;
   
   if (DISABLE_BACKEND) {
       // Skip backend operation
       console.log("[DEBUG] Backend disabled - skipping...");
       return;
   }
   ```

3. **Functions that check the flag**:
   - `startProctoringSession()` - Session start
   - `stopProctoringSession()` - Session stop
   - `checkExistingSession()` - Session check
   - `initWebSocket()` - WebSocket connection
   - `sendTabSwitchUpdate()` - Tab switch reporting
   - `mediaRecorder.onstop()` - Video upload

## Testing Checklist

### Frontend Only (Backend Disabled)
- [ ] Page loads without errors
- [ ] Fullscreen step works
- [ ] Camera step works
- [ ] Start button works
- [ ] Contest iframe loads
- [ ] Fullscreen exit warning shows
- [ ] Tab switches are detected (check console)
- [ ] Video recording works (check console for chunks)
- [ ] Console shows "Backend disabled" messages

### Full System (Backend Enabled)
- [ ] Backend server is running
- [ ] Session created on backend
- [ ] WebSocket connects successfully
- [ ] Tab switches sent to backend
- [ ] Video clips uploaded to backend
- [ ] Session stopped on backend

## Troubleshooting

### Issue: Backend connections still attempted
**Solution**: Check these in order:
1. `MASTER_DEBUG_ENABLED = True` in `debug.py`
2. `PROCTORING_DISABLE_BACKEND = True` in `debug.py`
3. Django server restarted after changes
4. Browser cache cleared
5. Check console for `DISABLE_BACKEND` value

### Issue: Proctoring not working at all
**Solution**:
1. Check if camera/fullscreen permissions granted
2. Look for JavaScript errors in console
3. Verify all security features are browser-compatible
4. Try different browser (Chrome/Firefox recommended)

## Best Practices

1. **Development**: Use `PROCTORING_DISABLE_BACKEND = True`
   - Faster iteration
   - No backend setup needed
   - Focus on frontend features

2. **Integration Testing**: Use `PROCTORING_DISABLE_BACKEND = False`
   - Test full flow
   - Verify data persistence
   - Check backend integration

3. **Production**: Set `MASTER_DEBUG_ENABLED = False`
   - Disable all debug features
   - Force proper backend connection
   - Enable all security checks
