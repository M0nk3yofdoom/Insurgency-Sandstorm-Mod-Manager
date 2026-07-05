#!/usr/bin/env python3
"""
Main launcher application that provides a simple interface to start both insurgency_manager.py and console_generator.py
"""

import sys
import os
import threading
import time
import webview
import subprocess

def create_launcher_ui():
    """Create a launcher UI that allows starting both applications"""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insurgency Manager - Launcher</title>
        <style>
            :root {
                --bg: #171317;
                --surface: #2a2525;
                --accent: #DDBFA2;
                --text: #858F8B;
                --error: #AB381C;
                --border-radius: 4px;
            }

            body {
                background: var(--bg);
                color: var(--text);
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                display: flex;
                flex-direction: column;
                height: 100vh;
                overflow: hidden;
            }

            header {
                background: var(--surface);
                padding: 1rem 2rem;
                border-bottom: 1px solid #333;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            h1 { 
                margin: 0; 
                font-size: 1.5rem; 
                color: var(--accent); 
                text-transform: uppercase;
                font-weight: bold;
            }

            .container {
                display: flex;
                flex: 1;
                padding: 2rem;
                gap: 2rem;
                overflow: hidden;
            }

            .app-card {
                flex: 1;
                background: var(--surface);
                border: 1px solid #333;
                border-radius: var(--border-radius);
                padding: 2rem;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }

            .app-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
                color: var(--accent);
            }

            .app-title {
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: var(--accent);
            }

            .app-description {
                margin-bottom: 2rem;
                line-height: 1.6;
            }

            .launch-btn {
                padding: 12px 24px;
                background: var(--accent);
                color: var(--bg);
                border: none;
                border-radius: 0;
                cursor: pointer;
                font-weight: bold;
                transition: background 0.2s;
                font-size: 1rem;
                margin: 0 4px;
            }

            .launch-btn:hover {
                background: #9a68d0;
            }

            .status-bar {
                background: var(--surface);
                padding: 0.5rem 2rem;
                border-top: 1px solid #333;
                font-size: 0.8rem;
                display: flex;
                justify-content: space-between;
            }

            .status-text {
                color: var(--accent);
            }
        </style>
    </head>
    <body>
        <header>
            <h1>Insurgency Manager Launcher</h1>
        </header>
        
        <div class="container">
            <div class="app-card">
                <div class="app-icon">🎮</div>
                <h2 class="app-title">Mod Manager</h2>
                <p class="app-description">Manage your Insurgency:Sandstorm mods with a user-friendly interface. View, search, and organize your installed mods.</p>
                <button class="launch-btn" onclick="launchManager()">Launch Mod Manager</button>
            </div>
            
            <div class="app-card">
                <div class="app-icon">🔧</div>
                <h2 class="app-title">Console Generator</h2>
                <p class="app-description">Generate console commands for your mods. Create and manage custom console configurations for the game.</p>
                <button class="launch-btn" onclick="launchGenerator()">Launch Console Generator</button>
            </div>
        </div>
        
        <div class="status-bar">
            <div class="status-text">Ready</div>
            <div id="last-updated">Last updated: --</div>
        </div>

        <script>
            // Keep track of running processes
            let runningProcesses = [];
            
            function launchManager() {
                window.pywebview.api.launch_manager();
            }
            
            function launchGenerator() {
                window.pywebview.api.launch_generator();
            }
            
            // Update timestamp
            function updateTimestamp() {
                const now = new Date();
                const timeString = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                const dateString = now.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
                document.getElementById('last-updated').textContent = 'Last updated: ' + timeString + ' ' + dateString;
            }
            
            updateTimestamp();
            setInterval(updateTimestamp, 60000);
        </script>
    </body>
    </html>
    """
    
    return html_content

def launch_manager():
    """Launch the insurgency manager application"""
    try:
        import insurgency_manager
        insurgency_manager.start_manager()
    except Exception as e:
        print(f"Error launching manager: {e}")

def launch_generator():
    """Launch the console generator application"""
    try:
        import console_generator
        console_generator.main()
    except Exception as e:
        print(f"Error launching generator: {e}")


def start_launcher():
    """Start the launcher application"""
    
    # Create the HTML content
    html_content = create_launcher_ui()
    
    # Create a simple API for launching applications
    class LauncherAPI:
        def launch_manager(self):
            import threading
            thread = threading.Thread(target=launch_manager)
            thread.daemon = True
            thread.start()
            return {"status": "launched"}
            
        def launch_generator(self):
            import threading
            thread = threading.Thread(target=launch_generator)
            thread.daemon = True
            thread.start()
            return {"status": "launched"}
    
    # Start the launcher window
    api = LauncherAPI()
    window = webview.create_window('Insurgency Manager Launcher', 
                                   html=html_content, 
                                   width=1000, 
                                   height=600,
                                   js_api=api)
    webview.start()

if __name__ == "__main__":
    start_launcher()