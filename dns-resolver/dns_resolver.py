#!/usr/bin/env python3
"""
Custom DNS Resolver Script
Resolves hostnames using entries from host.txt file without modifying system hosts file.
Supports both Python and PowerShell execution environments.
"""

import os
import sys
import socket
import subprocess
import platform
from pathlib import Path
import re
import argparse
from typing import Dict, List, Tuple, Optional

class CustomDNSResolver:
    def __init__(self, hosts_file_path: str = None):
        """Initialize the DNS resolver with custom hosts file."""
        self.script_dir = Path(__file__).parent.absolute()
        self.hosts_file = hosts_file_path or self.script_dir / "host.txt"
        self.host_mappings: Dict[str, str] = {}
        self.load_hosts()
    
    def load_hosts(self) -> None:
        """Load host mappings from the hosts file."""
        try:
            if not self.hosts_file.exists():
                print(f"Warning: {self.hosts_file} not found. Creating example file...")
                self.create_example_hosts_file()
                return
            
            self.host_mappings.clear()
            with open(self.hosts_file, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse line: IP followed by hostname(s)
                    parts = line.split()
                    if len(parts) < 2:
                        print(f"Warning: Invalid format at line {line_num}: {line}")
                        continue
                    
                    ip_address = parts[0]
                    hostnames = parts[1:]
                    
                    # Validate IP address
                    if not self.is_valid_ip(ip_address):
                        print(f"Warning: Invalid IP address at line {line_num}: {ip_address}")
                        continue
                    
                    # Add all hostnames for this IP
                    for hostname in hostnames:
                        self.host_mappings[hostname.lower()] = ip_address
            
            print(f"Loaded {len(self.host_mappings)} host mappings from {self.hosts_file}")
            
        except Exception as e:
            print(f"Error loading hosts file: {e}")
            sys.exit(1)
    
    def create_example_hosts_file(self) -> None:
        """Create an example hosts file with the provided format."""
        example_content = """# Custom Host Mappings
# Format: IP_ADDRESS    HOSTNAME [ADDITIONAL_HOSTNAMES...]
# Lines starting with # are comments

192.168.40.10   nginx.localdomain
192.168.40.11   nginx1.localdomain
192.168.40.12   nginx2.localdomain

# You can add multiple hostnames for the same IP
# 192.168.1.100   myserver.local myserver.dev myserver
"""
        try:
            with open(self.hosts_file, 'w', encoding='utf-8') as file:
                file.write(example_content)
            print(f"Created example hosts file: {self.hosts_file}")
        except Exception as e:
            print(f"Error creating example hosts file: {e}")
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Validate IP address format."""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def resolve_hostname(self, hostname: str) -> Optional[str]:
        """Resolve hostname to IP address using custom mappings."""
        hostname_lower = hostname.lower()
        return self.host_mappings.get(hostname_lower)
    
    def reverse_resolve(self, ip_address: str) -> List[str]:
        """Find all hostnames mapped to a given IP address."""
        return [hostname for hostname, ip in self.host_mappings.items() if ip == ip_address]
    
    def list_all_mappings(self) -> None:
        """Display all current host mappings."""
        if not self.host_mappings:
            print("No host mappings loaded.")
            return
        
        print("\nCurrent Host Mappings:")
        print("-" * 50)
        
        # Group by IP address for better display
        ip_groups = {}
        for hostname, ip in self.host_mappings.items():
            if ip not in ip_groups:
                ip_groups[ip] = []
            ip_groups[ip].append(hostname)
        
        for ip, hostnames in sorted(ip_groups.items()):
            hostnames_str = ", ".join(sorted(hostnames))
            print(f"{ip:<15} → {hostnames_str}")
    
    def test_connectivity(self, hostname: str, port: int = 80, timeout: int = 5) -> bool:
        """Test connectivity to resolved hostname."""
        ip_address = self.resolve_hostname(hostname)
        if not ip_address:
            print(f"Cannot resolve hostname: {hostname}")
            return False
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            
            if result == 0:
                print(f"{hostname} ({ip_address}) is reachable on port {port}")
                return True
            else:
                print(f"{hostname} ({ip_address}) is not reachable on port {port}")
                return False
                
        except Exception as e:
            print(f"Error testing connectivity to {hostname}: {e}")
            return False
    
    def ping_host(self, hostname: str, count: int = 4) -> bool:
        """Ping the resolved hostname."""
        ip_address = self.resolve_hostname(hostname)
        if not ip_address:
            print(f"Cannot resolve hostname: {hostname}")
            return False
        
        # Determine ping command based on OS
        system = platform.system().lower()
        if system == "windows":
            cmd = ["ping", "-n", str(count), ip_address]
        else:
            cmd = ["ping", "-c", str(count), ip_address]
        
        try:
            print(f"Pinging {hostname} ({ip_address})...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"Ping successful to {hostname} ({ip_address})")
                return True
            else:
                print(f"Ping failed to {hostname} ({ip_address})")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"Ping timeout for {hostname} ({ip_address})")
            return False
        except Exception as e:
            print(f"Error pinging {hostname}: {e}")
            return False
    
    def reload_hosts(self) -> None:
        """Reload hosts file."""
        print("Reloading hosts file...")
        self.load_hosts()
    
    def search_hostname(self, pattern: str) -> Dict[str, str]:
        """Search for hostnames matching a pattern."""
        results = {}
        pattern_lower = pattern.lower()
        
        for hostname, ip in self.host_mappings.items():
            if pattern_lower in hostname:
                results[hostname] = ip
        
        return results

def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(
        description="Custom DNS Resolver - Resolve hostnames from host.txt file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dns_resolver.py resolve nginx.localdomain
  python dns_resolver.py resolve --all
  python dns_resolver.py list
  python dns_resolver.py ping nginx1.localdomain
  python dns_resolver.py ping --all
  python dns_resolver.py test nginx2.localdomain 443
  python dns_resolver.py test --all --port 443
  python dns_resolver.py search nginx
        """
    )
    
    parser.add_argument('command', choices=['resolve', 'list', 'ping', 'test', 'search', 'reload'],
                       help='Command to execute')
    parser.add_argument('hostname', nargs='?', help='Hostname to resolve/ping/test')
    parser.add_argument('--all', '-a', action='store_true', help='Apply command to all hosts')
    parser.add_argument('--port', '-p', type=int, default=80, help='Port for connectivity test (default: 80)')
    parser.add_argument('--count', '-c', type=int, default=4, help='Ping count (default: 4)')
    parser.add_argument('--hosts-file', '-f', help='Path to custom hosts file')
    
    args = parser.parse_args()
    
    # Initialize resolver
    resolver = CustomDNSResolver(args.hosts_file)
    
    if args.command == 'resolve':
        if args.all:
            print("\nResolving all hosts:")
            print("-" * 40)
            for hostname, ip in sorted(resolver.host_mappings.items()):
                print(f"{hostname} → {ip}")
        else:
            if not args.hostname:
                print("Hostname required for resolve command (or use --all)")
                sys.exit(1)
            
            ip_address = resolver.resolve_hostname(args.hostname)
            if ip_address:
                print(f"{args.hostname} → {ip_address}")
            else:
                print(f"Cannot resolve: {args.hostname}")
                sys.exit(1)
    
    elif args.command == 'list':
        resolver.list_all_mappings()
    
    elif args.command == 'ping':
        if args.all:
            print("\nPinging all hosts:")
            print("-" * 40)
            successful_hosts = []
            failed_hosts = []
            
            for hostname in sorted(resolver.host_mappings.keys()):
                success = resolver.ping_host(hostname, args.count)
                if success:
                    successful_hosts.append(hostname)
                else:
                    failed_hosts.append(hostname)
            
            # Summary
            print(f"\nSummary:")
            print(f"Successful pings: {len(successful_hosts)}")
            print(f"Failed pings: {len(failed_hosts)}")
            
            if failed_hosts:
                print(f"Failed hosts: {', '.join(failed_hosts)}")
            
            # Only exit with error code if ALL hosts failed, not just some
            if len(successful_hosts) == 0 and len(failed_hosts) > 0:
                sys.exit(1)
        else:
            if not args.hostname:
                print("Hostname required for ping command (or use --all)")
                sys.exit(1)
            
            success = resolver.ping_host(args.hostname, args.count)
            if not success:
                sys.exit(1)
    
    elif args.command == 'test':
        if args.all:
            print(f"\nTesting connectivity to all hosts on port {args.port}:")
            print("-" * 50)
            successful_hosts = []
            failed_hosts = []
            
            for hostname in sorted(resolver.host_mappings.keys()):
                success = resolver.test_connectivity(hostname, args.port)
                if success:
                    successful_hosts.append(hostname)
                else:
                    failed_hosts.append(hostname)
            
            # Summary
            print(f"\nSummary:")
            print(f"Successful: {len(successful_hosts)}")
            print(f"Failed: {len(failed_hosts)}")
            
            if failed_hosts:
                print(f"Failed hosts: {', '.join(failed_hosts)}")
            
            # Only exit with error code if ALL hosts failed, not just some
            if len(successful_hosts) == 0 and len(failed_hosts) > 0:
                sys.exit(1)
        else:
            if not args.hostname:
                print("Hostname required for test command (or use --all)")
                sys.exit(1)
            
            success = resolver.test_connectivity(args.hostname, args.port)
            if not success:
                sys.exit(1)
    
    elif args.command == 'search':
        if not args.hostname:
            print("Search pattern required for search command")
            sys.exit(1)
        
        results = resolver.search_hostname(args.hostname)
        if results:
            print(f"\nSearch results for '{args.hostname}':")
            print("-" * 40)
            for hostname, ip in sorted(results.items()):
                print(f"{ip:<15} → {hostname}")
        else:
            print(f"No matches found for pattern: {args.hostname}")
    
    elif args.command == 'reload':
        resolver.reload_hosts()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)