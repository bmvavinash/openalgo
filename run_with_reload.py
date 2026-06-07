#!/usr/bin/env python3
"""
Alternative server startup script with better auto-reload support
Uses Flask's built-in reloader which works more reliably than SocketIO's
"""
import os
import sys

# Set environment for development
os.environ['FLASK_DEBUG'] = 'True'
os.environ['FLASK_ENV'] = 'development'

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import after path is set
from app import app, socketio

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run OpenAlgo server with auto-reload')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--no-reload', action='store_true', help='Disable auto-reload')
    
    args = parser.parse_args()
    
    print("="*60)
    print("OPENALGO SERVER - DEVELOPMENT MODE WITH AUTO-RELOAD")
    print("="*60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Auto-reload: {'Disabled' if args.no_reload else 'Enabled'}")
    print("="*60)
    print()
    print("The server will automatically reload when Python files change.")
    print("Press Ctrl+C to stop the server.")
    print()
    
    # Use Flask's run method for better reload support, but this won't work with SocketIO
    # So we'll use socketio.run but with explicit reloader settings
    socketio.run(
        app, 
        host=args.host, 
        port=args.port, 
        debug=True, 
        use_reloader=not args.no_reload,
        allow_unsafe_werkzeug=True
    )










