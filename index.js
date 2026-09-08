const express = require('express');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static(__dirname));

// Serve the HTML page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Endpoint to get server PID
app.get('/api/pid', (req, res) => {
    res.json({ pid: process.pid });
});

// Endpoint to execute commands
app.post('/api/exec', (req, res) => {
    const { command } = req.body;

    if (!command || typeof command !== 'string') {
        return res.status(400).json({ 
            error: 'Invalid command. Please provide a command string.' 
        });
    }

    // Split command into parts (handle quoted arguments)
    const parts = command.trim().split(/\s+/);
    const cmd = parts[0];
    const args = parts.slice(1);

    // Security: Block dangerous commands
    const blockedCommands = ['rm', 'rmdir', 'del', 'format', 'mkfs', 'dd', 'shutdown', 'reboot'];
    if (blockedCommands.includes(cmd)) {
        return res.status(403).json({
            error: `Command "${cmd}" is blocked for security reasons.`
        });
    }

    let stdout = '';
    let stderr = '';
    let exitCode = null;

    try {
        // Spawn the child process
        const child = spawn(cmd, args, {
            shell: true, // Use shell for better command support
            env: process.env,
            cwd: process.cwd(),
            timeout: 30000, // 30 second timeout
        });

        // Collect stdout
        child.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        // Collect stderr
        child.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        // Handle process exit
        child.on('close', (code) => {
            exitCode = code;
            // Send response after process closes
            res.json({
                stdout: stdout.trimEnd(),
                stderr: stderr.trimEnd(),
                exitCode: exitCode,
                pid: child.pid
            });
        });

        // Handle errors (e.g., command not found)
        child.on('error', (err) => {
            console.error('Spawn error:', err);
            if (!res.headersSent) {
                res.status(500).json({
                    error: `Failed to execute command: ${err.message}`,
                    stdout: stdout,
                    stderr: stderr
                });
            }
        });

    } catch (err) {
        console.error('Execution error:', err);
        res.status(500).json({
            error: `Internal error: ${err.message}`
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Terminal server running at http://localhost:${PORT}`);
    console.log(`📡 Server PID: ${process.pid}`);
    console.log(`⚠️  Blocked commands: rm, rmdir, del, format, mkfs, dd, shutdown, reboot`);
});
