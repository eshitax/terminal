from flask import Flask, request, jsonify, send_file, render_template_string
import subprocess
import os
import signal
import platform
import json
from datetime import datetime

app = Flask(__name__)

# Security: Block dangerous commands
BLOCKED_COMMANDS = [
    'rm', 'rmdir', 'del', 'format', 'mkfs', 'dd', 
    'shutdown', 'reboot', 'poweroff', 'halt',
    'mkfs.ext4', 'mkfs.ntfs', 'fdisk', 'parted'
]

# Get server PID
SERVER_PID = os.getpid()

def is_command_blocked(command):
    """Check if command is in blocked list"""
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False
    base_cmd = cmd_parts[0].lower()
    return base_cmd in BLOCKED_COMMANDS

@app.route('/')
def index():
    """Serve the HTML interface"""
    with open('index.html', 'r') as f:
        return render_template_string(f.read())

@app.route('/api/pid', methods=['GET'])
def get_pid():
    """Return server process ID"""
    return jsonify({
        'pid': SERVER_PID,
        'platform': platform.system(),
        'python_version': platform.python_version()
    })

@app.route('/api/exec', methods=['POST'])
def execute_command():
    """Execute a system command using subprocess"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'error': 'No command provided'}), 400
        
        command = data['command'].strip()
        if not command:
            return jsonify({'error': 'Empty command'}), 400

        # Security check
        if is_command_blocked(command):
            return jsonify({
                'error': f'Command "{command.split()[0]}" is blocked for security reasons',
                'stdout': '',
                'stderr': '',
                'exit_code': -1
            }), 403

        # Determine shell based on platform
        if platform.system() == 'Windows':
            shell_cmd = ['cmd', '/c', command]
        else:
            shell_cmd = ['sh', '-c', command]

        # Execute command with timeout
        try:
            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=os.getcwd(),
                env=os.environ.copy()
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            exit_code = result.returncode

            return jsonify({
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': exit_code,
                'pid': result.pid if hasattr(result, 'pid') else None
            })

        except subprocess.TimeoutExpired:
            return jsonify({
                'error': 'Command timed out after 30 seconds',
                'stdout': '',
                'stderr': '',
                'exit_code': -1
            }), 408

        except FileNotFoundError:
            return jsonify({
                'error': f'Command not found: {command.split()[0]}',
                'stdout': '',
                'stderr': '',
                'exit_code': -1
            }), 404

    except Exception as e:
        return jsonify({
            'error': f'Server error: {str(e)}',
            'stdout': '',
            'stderr': '',
            'exit_code': -1
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'pid': SERVER_PID,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Terminal server running at http://localhost:{port}")
    print(f"📡 Server PID: {SERVER_PID}")
    print(f"🖥️  Platform: {platform.system()}")
    print(f"⚠️  Blocked commands: {', '.join(BLOCKED_COMMANDS)}")
    print(f"🔒 Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=port, debug=False)
