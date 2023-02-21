###
### IPK:    Project 1
### 
### Author: Dominik Horky
### Login:  xhorky32
### FIT VUT, 2BIT 
###

import os
import sys
from pathlib import Path
import socket
import requests
import argparse
import random

###
### DEFINITIONS
###

GET_AGENT = 'xhorky32'
BUFF_SIZE = 4096
SOCKET_TIMEOUT = 8     # seconds
GETALL = False
VERBOSE = False
INDEX_TEMP_FNAME = "index.tmp." + str(random.randint(0, 999999999999999))
KEEP_INDEX = False
DONT_REPLACE = False
default_cwd = os.getcwd()

def verbose_print(message):
    if (VERBOSE):
        print(message)

def download_file():
    os.chdir(default_cwd)
    f_length = 0
    
    if (GETALL and source_file == "index"):
        output_file = open(INDEX_TEMP_FNAME, "wb")
    else:
        if (DONT_REPLACE and os.path.isfile(source_file)):
            verbose_print("File '" + source_file + "' exists, skipping. [-r]")
            return 0
        else:
            output_file = open(source_file, "wb")

    get_request = "GET " + source_file + " FSP/1.0\r\nAgent: " + GET_AGENT + "\r\nHostname: " + get_hostname + "\r\n\r\n"
    request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    request.settimeout(SOCKET_TIMEOUT)
    request.connect((source_ip, source_port))
    request.sendto(bytes(get_request, 'ascii'), (source_ip, source_port))
    try:
        received = request.recv(BUFF_SIZE)
    except InterruptedError as err:
        sys.exit("Error while downloading file [request interrupted]")
    except socket.timeout as err:
        sys.exit("Error while downloading file [request timed out]")
    except socket.error as err:
        sys.exit("Error while downloading file [OS error]")
    except socket.herror as err:
        sys.exit("Error while downloading file [address related OS error]")
    except socket.gaierror as err:
        sys.exit("Error while downloading file [address related OS error]")
    except:
        sys.exit("Error while downloading file [unknown exception]")

    first = True
    while received:
        if (first == True):
            first = False
            output_lines = received.decode('ascii').split('\n')
            header_1 = output_lines[0]
            header_2 = output_lines[1]

            result = header_1.split()[1]
            if (result != "Success"):
                sys.exit('Error: ' + output_lines[3])

            expected_length = int(header_2.split(':')[1])

            print_from = 2
            if (len(output_lines[2]) <= 1):
                print_from = print_from + 1
            if (len(output_lines[3]) <= 1):
                print_from = print_from + 1

            line_cnt = 0
            size = len(output_lines)
            for line in output_lines:
                if (line_cnt >= print_from):
                    output_file.write(bytes(line, 'ascii'))
                    f_length = f_length + len(line)
                line_cnt = line_cnt + 1
        else:
            output_file.write(bytes(received))
            f_length = f_length + len(received)
            
        received = request.recv(BUFF_SIZE)
    request.close()

    if (f_length != expected_length) or (source_file == "index" and f_length - len(header_1) - len(header_2) != expected_length):
        verbose_print("Warning: Expected response of '" + str(expected_length) + "' characters, but got '" + str(f_length) + "' characters.")
    else:
        verbose_print("Filesize check is OK.")

def prepare_space():
    source_file_path = source_file.split("/")

    a = 1
    for folder in source_file_path:
        if (a != len(source_file_path)):
            try:
                os.mkdir(folder)
                os.chdir(folder)
                verbose_print("Created directory '" + folder + "' in '" + os.getcwd() + "'")
            except FileExistsError as exc:
                verbose_print("Directory '" + folder + "' already exists in '" + os.getcwd() + "' (ignoring)")
                os.chdir(folder)
                pass
        else:
            if (folder == "*"):
                verbose_print("Detected GETALL request.")
                return True
        a = a + 1
    return False

###
### SCRIPT
###

#
## parse script arguments
#

parser = argparse.ArgumentParser(description='Client downloads file/s from servers. Downloaded file will be stored in current working directory. If error occurs, file/s won\'t be downloaded. ')
parser.add_argument('-i', required=False, action='store_true',
                    help='Download \'index\' file when requesting GETALL.')
parser.add_argument('-v', required=False, action='store_true',
                    help='Verbose option (be more talkative).')
parser.add_argument('-r', required=False, action='store_true',
                    help='Do not replace or overwrite existing files.')
required = parser.add_argument_group('required arguments')
required.add_argument('-n', metavar='NAMESERVER', required=True, type=str,
                    help='IP address and port of nameserver')
required.add_argument('-f', metavar='SURL', required=True, type=str,
                    help='SURL of downloaded file (fsp protocol)')

args = parser.parse_args()
VERBOSE = args.v
KEEP_INDEX = args.i
DONT_REPLACE = args.r

nameserver = args.n.split(':')
temp = args.f.split('/')

#
## arguments syntax check
#

if (len(nameserver) < 2 or not nameserver[1].isdigit() or len(nameserver[0].split('.')) != 4 or not nameserver[0].split('.')[0].isdigit() or not nameserver[0].split('.')[1].isdigit() or not nameserver[0].split('.')[2].isdigit() or not nameserver[0].split('.')[3].isdigit()):
    sys.exit("Error: bad syntax of NAMESERVER (expected IPv4 address with port in format 'N.N.N.N:PPPP' where N and P are digits)")

if (len(temp) < 4 or temp[1] != "" or temp[2] == "" or temp[3] == "" or temp[0].lower() != "fsp:"):
    sys.exit("Error: bad syntax of SURL (expected: 'fsp://server.hostname/filepath')")

#
## prepare data
#

temp2 = temp[0].split(':')

ns_ip = nameserver[0]
ns_port = int(nameserver[1])
ns = (ns_ip, ns_port)
protocol = temp2[0]
source_address = temp[2]

source_file = temp[3]


## client
#

x = 0
for part_path in temp:
    if (x > 3):
        source_file = source_file + "/" + part_path
    x = x + 1

get_hostname = source_address

# > get filesystem IP address
#
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientSocket.settimeout(SOCKET_TIMEOUT)
clientSocket.sendto(bytes('WHEREIS ' + source_address, 'ascii'), ns)

try:
    received, address = clientSocket.recvfrom(BUFF_SIZE)
except InterruptedError as err:
    sys.exit("Error obtaining filesystem IP address [request interrupted]")
except socket.timeout as err:
    sys.exit("Error obtaining filesystem IP address [request timed out]")
except socket.error as err:
    sys.exit("Error obtaining filesystem IP address [OS error]")
except socket.herror as err:
    sys.exit("Error obtaining filesystem IP address [address related OS error]")
except socket.gaierror as err:
    sys.exit("Error obtaining filesystem IP address [address related OS error]")
except:
    sys.exit("Error obtaining filesystem IP address [unknown exception]")

clientSocket.close()

# extract IP & port from obtained data

data = received.decode('ascii').split()
err_msg = ""

if (data[0] != "OK"):
    b = 0
    for data_text in data:
        if (b > 0):
            err_msg = err_msg + " " + data_text
        b = b + 1
    
    if (err_msg == " Not Found"):
        err_msg = "Filesystem not found."
    else:
        err_msg = "Unknown error."
    sys.exit("Error: " + err_msg)


source = data[1].split(':')

source_ip = source[0]
source_port = int(source[1])

verbose_print("Address '" + source_address + "' found at '" + source_ip + "' (port: '" + source[1] + "')")

# > prepare filesystem structure and check for GETALL request
#

GETALL = prepare_space()

# > download desired file
# > if GETALL request is present, download index first and then download everything
#

if (GETALL):
    source_file = "index"
    verbose_print("Downloading temporary 'index' file.")
else:
    verbose_print("Downloading file: " + source_file)

download_file()

if (GETALL):
    index_def = open(INDEX_TEMP_FNAME, "r")
    index = index_def.read().split("\n")
    for file in index:
        if (len(file) >= 1):
            verbose_print("Downloading file: " + file)
            source_file = file
            prepare_space()
            download_file()
    if (KEEP_INDEX):
        if (DONT_REPLACE and os.path.isfile("index")):
            verbose_print("File 'index' already exists. Your index file will be named as '" + INDEX_TEMP_FNAME + "'. [-r]")
        else:    
            os.rename(INDEX_TEMP_FNAME, "index")
        verbose_print("Keeping index file. [-i]")
    else:
        verbose_print("Removed temporary 'index' file.")
        os.remove(INDEX_TEMP_FNAME)

# > end of the script
#

verbose_print("Success!")
exit(0)
