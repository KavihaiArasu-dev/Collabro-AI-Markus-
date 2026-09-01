# Run Command Behavior Rule

When the user gives the prompt "run" or asks to run/start the project, always ensure all three components of the Markus AI ecosystem are launched:

1. **OmniRoute AI Gateway**:
   - Command: `omniroute serve --no-open`
   - Port: `20128`

2. **Markus Backend Server**:
   - Directory: `markus/`
   - Command: `.\venv\Scripts\python.exe main.py`
   - Port: `8000`

3. **Markus Frontend UI**:
   - Directory: `markus/apps/frontend/`
   - Command: `npm run dev`
   - Port: `5173`

Launch them as background daemons (`IsDaemon: true`) if running via tools, and report their health status and URLs to the user.
