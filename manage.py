#!/usr/bin/env python3
"""
Service management script for CodeSnippets application.
Provides commands to start, stop, restart, and check status of the service.
"""

import argparse
import os
import subprocess
import sys
import time


def run_command(command, check=True):
    """Execute a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def is_service_active():
    """Check if the service is currently active."""
    result = run_command("systemctl is-active codesnippets.service", check=False)
    return result.returncode == 0


def start_service():
    """Start the CodeSnippets service."""
    if is_service_active():
        print("Service is already running.")
        return

    print("Starting CodeSnippets service...")
    result = run_command("sudo systemctl start codesnippets.service")
    
    # Check if the service started successfully
    if is_service_active():
        print("Service started successfully.")
    else:
        print("Failed to start service. Check logs with 'journalctl -u codesnippets.service'")


def stop_service():
    """Stop the CodeSnippets service."""
    if not is_service_active():
        print("Service is not running.")
        return

    print("Stopping CodeSnippets service...")
    result = run_command("sudo systemctl stop codesnippets.service")
    
    # Wait briefly and check if the service has stopped
    time.sleep(2)
    if not is_service_active():
        print("Service stopped successfully.")
    else:
        print("Failed to stop service. Check logs with 'journalctl -u codesnippets.service'")


def restart_service():
    """Restart the CodeSnippets service."""
    print("Restarting CodeSnippets service...")
    result = run_command("sudo systemctl restart codesnippets.service")
    
    # Check if the service is running after restart
    if is_service_active():
        print("Service restarted successfully.")
    else:
        print("Failed to restart service. Check logs with 'journalctl -u codesnippets.service'")


def check_status():
    """Check and display the status of the CodeSnippets service."""
    print("Checking CodeSnippets service status...")
    run_command("systemctl status codesnippets.service", check=False)


def reload_systemd():
    """Reload systemd manager configuration."""
    print("Reloading systemd configuration...")
    run_command("sudo systemctl daemon-reload")


def enable_service():
    """Enable the service to start on boot."""
    print("Enabling CodeSnippets service to start on boot...")
    run_command("sudo systemctl enable codesnippets.service")
    print("Service enabled.")


def disable_service():
    """Disable the service from starting on boot."""
    print("Disabling CodeSnippets service from starting on boot...")
    run_command("sudo systemctl disable codesnippets.service")
    print("Service disabled.")


def main():
    parser = argparse.ArgumentParser(description="Manage the CodeSnippets service")
    
    # Create a subparser for the different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the service")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the service")
    
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart the service")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check service status")
    
    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable service to start on boot")
    
    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable service from starting on boot")
    
    # Reload command
    reload_parser = subparsers.add_parser("reload-systemd", help="Reload systemd configuration")
    
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "start":
        start_service()
    elif args.command == "stop":
        stop_service()
    elif args.command == "restart":
        restart_service()
    elif args.command == "status":
        check_status()
    elif args.command == "enable":
        enable_service()
    elif args.command == "disable":
        disable_service()
    elif args.command == "reload-systemd":
        reload_systemd()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()