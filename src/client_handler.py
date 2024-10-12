"""
Handler module for user input and client setup.
Provides command line interface for p2p file sharing client.
"""
from client import Client
from protocol import *
import asyncio
import sys
import os

def print_file_tree(start_path='.'):
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")

def display_menu():
    """Display main menu options"""
    print("\np2p file sharing client")
    print("-" * 30)
    print("[1] List available torrents")
    print("[2] Download a file")
    print("[3] Share a file")
    print("[4] Show help")
    print("[5] Quit")
    return input("Enter choice: ")

def display_help():
    """Display detailed help information"""
    help_text = """
Available Commands
-----------------
1. List available torrents
   View all shared files and their IDs currently available in the network

2. Download a file
   Get a file from the network using its torrent ID

3. Share a file
   Make your file available to others in the network

4. Show help
   Display this help message

5. Quit
   Exit the program
"""
    print(help_text)
    input("Press Enter to continue...")

def get_user_choice():
    """Get and validate user menu choice"""
    while True:
        try:
            # print_file_tree()
            choice = int(display_menu())
            if choice in range(1, 6):
                if choice == 1:
                    return [OPT_GET_LIST, None, None]
                elif choice == 2:
                    torrent_id = int(input("Enter torrent ID: "))
                    return [OPT_GET_TORRENT, torrent_id, None]
                elif choice == 3:
                    filename = input("Enter filename: ")
                    filename = "input/image.jpg"
                    return [OPT_UPLOAD_FILE, None, filename]
                elif choice == 4:
                    display_help()
                    return [0, None, None]
                else:  # choice == 5
                    return [-1, None, None]
            print("[error] invalid choice, please try again")
        except ValueError:
            print("[error] please enter a number")

def validate_ip(ip: str) -> bool:
    """Validate IP address format"""
    try:
        asyncio.streams.socket.inet_aton(ip)
        return True
    except asyncio.streams.socket.error:
        return False

def validate_port(port: str) -> bool:
    """Validate port number"""
    try:
        port_num = int(port)
        return 0 <= port_num <= 65535
    except ValueError:
        return False

def parse_arguments():
    """Parse and validate command line arguments"""
    args = sys.argv[1:]
    arg_count = len(args)
    
    if arg_count not in [2, 4]:
        print("Usage: client_handler.py [source ip] [source port] [tracker ip] [tracker port]")
        return None, None, None, None

    src_ip = args[0]
    src_port = args[1]
    dest_ip = args[2] if arg_count == 4 else None
    dest_port = args[3] if arg_count == 4 else None

    # Validate source IP and port
    if not validate_ip(src_ip):
        print("[error] invalid source IP address")
        return None, None, None, None
    
    if not validate_port(src_port):
        print("[error] invalid source port number")
        return None, None, None, None

    # Validate destination IP and port if provided
    if arg_count == 4:
        if not validate_ip(dest_ip):
            print("[error] invalid tracker IP address")
            return None, None, None, None
        
        if not validate_port(dest_port):
            print("[error] invalid tracker port number")
            return None, None, None, None

    return src_ip, src_port, dest_ip, dest_port

async def handle_client_operation(client, reader, writer, operation):
    """Handle a single client operation"""
    if not operation[0] > 0:
        writer.close()
        return True, None

    payload = client.create_server_request(
        opc=operation[0],
        torrent_id=operation[1],
        filename=operation[2]
    )

    if not payload:
        return True, None

    await client.send_message(writer, payload)
    print("receiving request from handler")
    result = await client.receive_message(reader)
    return False, result

async def handle_seeding_completion(client, reader, writer, dest_ip, dest_port, torrent_id):
    """Handle the transition from downloading to seeding"""
    writer.close()
    reader, writer = await client.register_to_tracker(dest_ip, dest_port)
    payload = client.create_server_request(opc=OPT_START_SEED, torrent_id=torrent_id)
    await client.send_message(writer, payload)
    result = await client.receive_message(reader)
    writer.close()
    return result

async def handle_seeding_termination(client, reader, writer, dest_ip, dest_port):
    """Handle cleanup when seeding is finished"""
    writer.close()
    reader, writer = await client.register_to_tracker(dest_ip, dest_port)
    payload = client.create_server_request(opc=OPT_STOP_SEED, torrent_id=client.torrent_id)
    await client.send_message(writer, payload)
    result = await client.receive_message(reader)
    writer.close()
    return result

async def run_client_loop(client, dest_ip, dest_port):
    """Main client operation loop"""
    while True:
        reader, writer = await client.register_to_tracker(dest_ip, dest_port)
        operation = get_user_choice()

        if operation[0] == -1:  # Exit
            writer.close()
            return

        should_continue, result = await handle_client_operation(client, reader, writer, operation)
        if should_continue:
            continue

        if result == RET_FINISHED_DOWNLOAD:
            result = await handle_seeding_completion(
                client, reader, writer, dest_ip, dest_port, operation[1]
            )

        if result == RET_FINSH_SEEDING:
            await handle_seeding_termination(client, reader, writer, dest_ip, dest_port)
            break

        if result != RET_SUCCESS:
            writer.close()

async def main():
    """Main entry point"""
    src_ip, src_port, dest_ip, dest_port = parse_arguments()
    
    if not src_ip or not src_port:
        return

    client = Client(src_ip, src_port)
    
    # Use default tracker address if not provided
    dest_ip = dest_ip or "127.0.0.1"
    dest_port = dest_port or "8888"
    
    print(f"[info] connecting to tracker at {dest_ip}:{dest_port}")
    print(f"[info] client address: {src_ip}:{src_port}")
    
    try:
        await run_client_loop(client, dest_ip, dest_port)
    except Exception as e:
        print(f"[error] unexpected error: {str(e)}")
    finally:
        print("[info] shutting down client")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[info] program terminated by user")