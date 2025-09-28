# Custom DNS Resolver

A Python script to resolve hostnames using a custom `host.txt` file, without modifying your system's hosts file. Supports both Python and PowerShell execution environments.

## Features
- Resolve hostnames to IP addresses using a local `host.txt` file
- List all custom host mappings
- Ping hosts by name (using custom mapping)
- Test TCP connectivity to hosts on a specified port
- Search hostnames by pattern
- Reload host mappings without restarting the script
- Cross-platform: works on Windows, Linux, and macOS

## File Structure
```
dns-resolver/
├── dns_resolver.py   # Main script
└── host.txt          # Custom hosts file (example provided)
```

## host.txt Format
- Each line: `<IP_ADDRESS> <HOSTNAME> [ADDITIONAL_HOSTNAMES...]`
- Lines starting with `#` are comments

**Example:**
```
# Custom Host Mappings
192.168.40.10   nginx.localdomain
192.168.40.11   nginx1.localdomain
192.168.40.12   nginx2.localdomain
# 192.168.1.100   myserver.local myserver.dev myserver
```

## Usage
Run the script with Python 3:

```sh
python dns_resolver.py <command> [hostname/pattern] [options]
```

### Commands
- `resolve <hostname>`: Resolve a hostname to its IP address
- `resolve --all`: Show all host-to-IP mappings
- `list`: List all current host mappings
- `ping <hostname>`: Ping a host by name
- `ping --all`: Ping all hosts
- `test <hostname> [--port PORT]`: Test TCP connectivity to a host (default port 80)
- `test --all [--port PORT]`: Test connectivity to all hosts
- `search <pattern>`: Search for hostnames containing a pattern
- `reload`: Reload the hosts file

### Options
- `--all, -a`: Apply command to all hosts
- `--port, -p`: Specify port for connectivity test (default: 80)
- `--count, -c`: Number of ping attempts (default: 4)
- `--hosts-file, -f`: Path to a custom hosts file

### Examples
```sh
python dns_resolver.py resolve nginx.localdomain
python dns_resolver.py resolve --all
python dns_resolver.py list
python dns_resolver.py ping nginx1.localdomain
python dns_resolver.py ping --all
python dns_resolver.py test nginx2.localdomain 443
python dns_resolver.py test --all --port 443
python dns_resolver.py search nginx
```

## Notes
- If `host.txt` does not exist, the script will create an example file.
- Hostname lookups are case-insensitive.
- The script does not modify your system's DNS or hosts file.

## Requirements
- Python 3.x
- Works on Windows, Linux, and macOS

## License
MIT
