#!/usr/bin/env python3
# Advanced terminator that detects and terminates key.py keylogger using Ctrl+C (SIGINT)
# Also captures system information about the attacker
# Usage: python3 advanced_terminator.py [--interval 1] [--auto]

import argparse
import os
import time
import sys
import psutil
import signal
from pathlib import Path
import subprocess
import threading
import platform
import socket
import json
from datetime import datetime

def get_system_info(pid):
    """Gather system information about the process and its environment"""
    system_info = {
        "timestamp": datetime.now().isoformat(),
        "target_process": {},
        "system_details": {},
        "network_info": {}
    }
    
    try:
        # Get process details
        proc = psutil.Process(pid)
        with proc.oneshot():
            system_info["target_process"] = {
                "pid": pid,
                "name": proc.name(),
                "exe": proc.exe(),
                "cmdline": proc.cmdline(),
                "username": proc.username(),
                "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                "cwd": proc.cwd(),
                "status": proc.status()
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        system_info["target_process"]["error"] = str(e)
    
    # Get system information
    try:
        system_info["system_details"] = {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "processor": platform.processor(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    except Exception as e:
        system_info["system_details"]["error"] = str(e)
    
    # Get network information
    try:
        connections = []
        for conn in psutil.net_connections():
            if conn.pid == pid:
                connections.append({
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "laddr": conn.laddr,
                    "raddr": conn.raddr,
                    "status": conn.status
                })
        system_info["network_info"]["connections"] = connections
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        system_info["network_info"]["error"] = str(e)
    
    return system_info

def desktop_notify(summary, body=""):
    """Send desktop notification if available"""
    try:
        subprocess.run(["notify-send", summary, body], check=False, 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    except Exception as e:
        print(f"[!] Notification error: {e}")

def find_keylogger_process():
    """Find processes named key.py specifically"""
    keylogger_procs = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                
                # Only target processes with key.py in their command line
                # More specific check to avoid false positives
                if ('key.py' in cmdline and 
                    not any(x in cmdline for x in ['advanced_terminator.py', 'terminator'])):
                    
                    # Additional verification - check if it's actually a Python process
                    if proc.info['name'] and ('python' in proc.info['name'].lower() or 
                                             'python3' in proc.info['name'].lower()):
                        keylogger_procs.append({
                            'pid': proc.pid,
                            'name': proc.info['name'] or 'unknown',
                            'cmdline': cmdline,
                            'username': proc.info['username'] or 'unknown'
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[!] Error processing process: {e}")
    except Exception as e:
        print(f"[!] Error in process iteration: {e}")
    
    return keylogger_procs

def send_ctrl_c_to_process(pid):
    """Send SIGINT (Ctrl+C) to process"""
    try:
        # Check if process still exists
        if not psutil.pid_exists(pid):
            return False, "Process does not exist"
            
        print(f"[>] Sending SIGINT to PID {pid}")
        os.kill(pid, signal.SIGINT)
        return True, "SIGINT sent to process"
        
    except ProcessLookupError:
        return False, "Process does not exist"
    except PermissionError:
        return False, "Permission denied (try running as root)"
    except Exception as e:
        return False, f"Error: {str(e)}"

def save_attacker_info(system_info):
    """Save attacker system information to a file"""
    try:
        filename = f"attacker_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(system_info, f, indent=2)
        print(f"[+] Attacker information saved to {filename}")
        return filename
    except Exception as e:
        print(f"[!] Failed to save attacker info: {e}")
        return None

def terminate_keylogger(pid, process_info):
    """Terminate keylogger process with proper cleanup and gather system info"""
    print("\n" + "="*60)
    print(f"[!] Terminating keylogger - PID {pid}")
    print(f"    Process : {process_info['name']}")
    print(f"    Command : {process_info['cmdline']}")
    print(f"    User    : {process_info['username']}")
    print("="*60)
    
    print("[*] Gathering system information about the attacker...")
    system_info = get_system_info(pid)
    save_attacker_info(system_info)
    
    if 'system_details' in system_info:
        sys_info = system_info['system_details']
        print(f"    OS         : {sys_info.get('os', 'unknown')} {sys_info.get('os_release', 'unknown')}")
        print(f"    Hostname   : {sys_info.get('hostname', 'unknown')}")
        print(f"    Arch       : {sys_info.get('architecture', 'unknown')}")
    
    success, message = send_ctrl_c_to_process(pid)
    print(f"[*] {message}")
    
    if success:
        # Give it a moment to terminate gracefully
        time.sleep(1)
        try:
            if psutil.pid_exists(pid):
                print("[!] Process still running after SIGINT, trying SIGTERM...")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)
                    if psutil.pid_exists(pid):
                        print("[!] Process still running, forcing SIGKILL...")
                        os.kill(pid, signal.SIGKILL)
                        print("[+] SIGKILL sent - process terminated forcefully")
                    else:
                        print("[+] Process terminated by SIGTERM")
                except Exception as e:
                    print(f"[!] Failed to send SIGTERM: {e}")
            else:
                print("[+] Process terminated cleanly by SIGINT (Ctrl+C)")
        except (ProcessLookupError, psutil.NoSuchProcess):
            print("[+] Process terminated successfully")
        except Exception as e:
            print(f"[!] Error checking process status: {e}")
    else:
        print(f"[!] Failed to terminate: {message}")
    
    try:
        desktop_notify("Keylogger Terminated", 
                      f"PID {pid} - {process_info['name']} has been terminated")
    except Exception as e:
        print(f"[!] Notification failed: {e}")

def monitor_and_terminate(interval=1, auto_mode=False):
    """Monitor for keylogger processes and terminate them"""
    print("[*] Advanced Keylogger Detector & Terminator")
    print("[*] Developed by: BSIT 3H STUDENTS")
    print("[*] School: Camarines Sur Polytechnic Colleges")
    print("[*] Address: Nabua, Camarines Sur")
    print("-" * 50)
    
    detected_count = 0
    
    try:
        while True:
            keyloggers = find_keylogger_process()
            
            if keyloggers:
                detected_count += 1
                print(f"\n[!] Detected {len(keyloggers)} keylogger process(es)")
                print("-" * 40)
                
                for i, proc in enumerate(keyloggers, 1):
                    print(f" {i}. PID {proc['pid']} - {proc['name']}")
                    print(f"    Command : {proc['cmdline']}")
                    print(f"    User    : {proc['username']}")
                    if i < len(keyloggers):
                        print()
                
                if auto_mode:
                    print("\n[*] Auto mode: terminating all detected keyloggers...")
                    print("-" * 40)
                    for proc in keyloggers:
                        terminate_keylogger(proc['pid'], proc)
                else:
                    print("\nChoose action:")
                    print("  1. Terminate all keyloggers")
                    print("  2. Terminate specific keylogger")
                    print("  3. Ignore and continue monitoring")
                    print("-" * 40)
                    
                    try:
                        choice = input("Enter choice (1-3): ").strip()
                        
                        if choice == '1':
                            print("\n[*] Terminating all keyloggers...")
                            print("-" * 40)
                            for proc in keyloggers:
                                terminate_keylogger(proc['pid'], proc)
                        elif choice == '2':
                            try:
                                pid_choice = int(input("Enter PID to terminate: "))
                                found = False
                                for proc in keyloggers:
                                    if proc['pid'] == pid_choice:
                                        print(f"\n[*] Terminating specific keylogger - PID {pid_choice}")
                                        print("-" * 40)
                                        terminate_keylogger(proc['pid'], proc)
                                        found = True
                                        break
                                if not found:
                                    print("[!] PID not found in detected keyloggers")
                            except ValueError:
                                print("[!] Invalid PID input")
                        elif choice == '3':
                            print("[*] Continuing monitoring...")
                        else:
                            print("[!] Invalid choice, continuing monitoring...")
                    except KeyboardInterrupt:
                        print("\n[!] Monitoring stopped by user")
                        break
                    except EOFError:
                        print("\n[!] Input closed, stopping...")
                        break
                    except Exception as e:
                        print(f"[!] Input error: {e}")
            else:
                status_msg = (f"[*] Scanning... no keyloggers detected (scan {detected_count})"
                              if detected_count > 0 else "[*] Scanning for keyloggers...")
                print(status_msg.ljust(60), end='\r')
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n[!] Monitoring stopped by user")
    except Exception as e:
        print(f"\n[!] Unexpected error: {str(e)}")
    finally:
        print(f"\n[+] Summary: detected {detected_count} keylogger instance(s)")

def continuous_protection(interval=2):
    """Run in background for continuous protection"""
    print("[*] Starting continuous protection mode")
    print("[*] Running in background. Keyloggers will be auto-terminated")
    print("-" * 50)
    
    try:
        while True:
            try:
                keyloggers = find_keylogger_process()
                for proc in keyloggers:
                    print(f"[!] Auto-terminating keylogger PID {proc['pid']}")
                    terminate_keylogger(proc['pid'], proc)
                time.sleep(interval)
            except Exception as e:
                print(f"[!] Error in protection loop: {e}")
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[!] Daemon mode stopped")
    except Exception as e:
        print(f"[!] Daemon error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Advanced Keylogger Terminator")
    parser.add_argument("--interval", "-i", type=float, default=1.0,
                       help="Scanning interval in seconds (default: 1)")
    parser.add_argument("--auto", "-a", action="store_true",
                       help="Auto-terminate without confirmation")
    parser.add_argument("--daemon", "-d", action="store_true",
                       help="Run as daemon for continuous protection")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List current keylogger processes and exit")
    args = parser.parse_args()
    
    try:
        import psutil
    except ImportError:
        print("[!] Error: psutil library required. Install with: pip install psutil")
        sys.exit(1)
    
    if args.list:
        try:
            keyloggers = find_keylogger_process()
            if keyloggers:
                print("[+] Found keylogger processes:")
                print("-" * 40)
                for proc in keyloggers:
                    print(f" PID     : {proc['pid']}")
                    print(f" Name    : {proc['name']}")
                    print(f" Command : {proc['cmdline']}")
                    print(f" User    : {proc['username']}")
                    print("-" * 40)
            else:
                print("[+] No keylogger processes found")
        except Exception as e:
            print(f"[!] Error listing processes: {e}")
        return
    
    if args.daemon:
        try:
            continuous_protection(args.interval)
        except KeyboardInterrupt:
            print("\n[!] Daemon mode stopped")
        except Exception as e:
            print(f"[!] Daemon error: {e}")
        return
    
    try:
        monitor_and_terminate(args.interval, args.auto)
    except Exception as e:
        print(f"[!] Unexpected error in main: {e}")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[!] Warning: not running as root. Some processes may not be accessible.")
        print("[!] Consider running with sudo for full functionality")
        print("-" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Program terminated by user")
    except Exception as e:
        print(f"[!] Critical error: {e}")
        sys.exit(1)
