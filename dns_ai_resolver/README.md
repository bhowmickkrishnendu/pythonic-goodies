# 🧩 DNS-AI Resolver (Perplexity + Python)

This project lets you **chat with an AI model through DNS TXT queries**, even when normal internet (HTTP/HTTPS) is blocked.  
It uses Python, the `dnslib` package, and the **Perplexity AI API**.

---

## ⚙️ How It Works
1. A DNS server listens on UDP port `5353` (you can later use 53 with root privileges).
2. Each DNS query (e.g., `dig @localhost -p 5353 what-is-future-of-ai TXT +short`) is treated as a prompt.
3. The server sends the query to the **Perplexity AI API** using your API key.
4. The model's short reply is returned as a **DNS TXT record**.

---

## 🧰 Requirements

### For Local Python Setup
- Python 3.8+
- `pip install dnslib requests python-dotenv`  
- A valid **Perplexity API key**

### For Docker Setup
- Docker installed on your system
- A valid **Perplexity API key**

---

## 🔑 Environment Setup (.env file)

### Step 1: Get Your Perplexity API Key

1. Go to [Perplexity API](https://www.perplexity.ai/settings/api)
2. Sign up or log in to your account
3. Navigate to API settings
4. Generate a new API key
5. Copy the API key (it starts with `pplx-`)

### Step 2: Create .env File

1. Copy the example environment file:
   ```bash
   cp file.env.example .env
   ```

2. Edit the `.env` file and add your API key:
   ```bash
   # .env
   PPLX_API_KEY=pplx-your_actual_perplexity_api_key_here
   ```

   Replace `pplx-your_actual_perplexity_api_key_here` with your actual Perplexity API key.

⚠️ **Important**: 
- Never commit your `.env` file to version control
- Keep your API key secure and private
- Add `.env` to your `.gitignore` file

---

## 🚀 Usage Options

### Option 1: Run Locally with Python

1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd dns-ai-resolver
   ```

2. Install dependencies:
   ```bash
   pip install dnslib requests python-dotenv
   ```

3. Set up your `.env` file (see Environment Setup above)

4. Run the DNS server:
   ```bash
   python dns_ai_resolver.py
   ```

5. Query the AI through DNS:
   ```bash
   dig @127.0.0.1 -p 5353 what-is-future-of-ai TXT +short
   ```

---

### Option 2: Run with Docker

#### Build the Docker Image

Build the Docker image with a custom tag:

```bash
docker build -t dns-ai-resolver .
```

This command:
- `-t dns-ai-resolver` — Tags the image with the name "dns-ai-resolver"
- `.` — Uses the current directory's Dockerfile

#### Run the Container

Run the container in detached mode:

```bash
docker run -d --name dnsai -p 5353:5353/udp --env-file .env dns-ai-resolver
```

Command breakdown:
- `-d` — Run container in detached mode (background)
- `--name dnsai` — Names the container "dnsai" for easy reference
- `-p 5353:5353/udp` — Maps UDP port 5353 from host to container
- `--env-file .env` — Loads environment variables from `.env` file
- `dns-ai-resolver` — The image name to run

#### Test from Host

Test the DNS resolver using `dig`:

```bash
dig @127.0.0.1 -p 5353 what-is-future-of-ai TXT +short
```

Example queries:
```bash
dig @127.0.0.1 -p 5353 explain-quantum-computing TXT +short
dig @127.0.0.1 -p 5353 best-programming-language-for-beginners TXT +short
dig @127.0.0.1 -p 5353 how-does-blockchain-work TXT +short
```

---

## 🐳 Docker Management Commands

### View Running Containers
```bash
docker ps
```

### View Container Logs
```bash
docker logs dnsai
```

### Follow Container Logs in Real-Time
```bash
docker logs -f dnsai
```

### Stop the Container
```bash
docker stop dnsai
```

### Start the Container Again
```bash
docker start dnsai
```

### Remove the Container
```bash
docker rm dnsai
```

### Remove the Image
```bash
docker rmi dns-ai-resolver
```

### Rebuild and Restart (Quick Update)
```bash
docker stop dnsai
docker rm dnsai
docker build -t dns-ai-resolver .
docker run -d --name dnsai -p 5353:5353/udp --env-file .env dns-ai-resolver
```

---

## 🧠 Advanced Configuration

### Using Standard DNS Port (53)

To use the standard DNS port 53 instead of 5353:

**On Linux/Mac (requires root):**
```bash
sudo python dns_ai_resolver.py
```

**With Docker:**
```bash
docker run -d --name dnsai -p 53:5353/udp --env-file .env dns-ai-resolver
```

⚠️ **Note**: Port 53 typically requires root/administrator privileges and may conflict with existing DNS services.

### Exposing to Network

To make the DNS resolver accessible from other machines on your network:

```bash
docker run -d --name dnsai -p 0.0.0.0:5353:5353/udp --env-file .env dns-ai-resolver
```

Then query from another machine:
```bash
dig @<your-host-ip> -p 5353 what-is-kubernetes TXT +short
```

---

## 🔍 Troubleshooting

### API Key Issues

**Error: "Missing PPLX_API_KEY in .env file"**
- Ensure `.env` file exists in the same directory
- Verify the file contains `PPLX_API_KEY=your_key_here`
- Make sure there are no extra spaces around the `=` sign

**Error: "API Error: 401"**
- Your API key is invalid or expired
- Generate a new key from Perplexity API settings

### Container Issues

**Container exits immediately:**
```bash
docker logs dnsai
```
Check logs for error messages about missing API key or dependencies.

**Port already in use:**
```bash
# Check what's using port 5353
sudo lsof -i :5353

# Use a different port
docker run -d --name dnsai -p 5454:5353/udp --env-file .env dns-ai-resolver
```

**Cannot query DNS:**
- Ensure the container is running: `docker ps`
- Check firewall settings allow UDP traffic on port 5353
- Verify you're using the correct IP address

### Testing Without dig

If `dig` is not available, use Python:

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(b'\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x04test\x00\x00\x10\x00\x01', ('127.0.0.1', 5353))
print(sock.recv(1024))
```

Or use `nslookup`:
```bash
nslookup -type=TXT what-is-AI 127.0.0.1 -port=5353
```

---

## 📁 Project Structure

```
dns-ai-resolver/
├── dns_ai_resolver.py    # Main Python DNS server script
├── Dockerfile            # Multi-stage Docker build configuration
├── file.env.example      # Example environment file
├── .env                  # Your actual API key (git-ignored)
├── .gitignore           # Git ignore file
└── README.md            # This file
```

---

## 🧠 Technical Notes

- **Model Used**: `sonar` (Perplexity's conversational model)
- **Response Limit**: DNS TXT records are limited to ~200 characters
- **Timeout**: API requests timeout after 15 seconds
- **Temperature**: Set to 0.2 for more focused, deterministic responses
- **Docker Image Size**: ~50MB (using multi-stage build with Alpine)

---

## 🪶 Example Output

```bash
$ dig @127.0.0.1 -p 5353 what-is-future-of-ai TXT +short
"AI will continue to shape automation, science, and creativity in the next decade."

$ dig @127.0.0.1 -p 5353 explain-kubernetes-in-simple-terms TXT +short
"Kubernetes orchestrates containers across multiple servers, automating deployment, scaling, and management of applications."
```

---

## 🔒 Security Considerations

1. **API Key Protection**: Never expose your `.env` file or commit it to git
2. **Network Exposure**: Be cautious when exposing to public networks
3. **Rate Limiting**: Perplexity API has rate limits; implement caching if needed
4. **Input Validation**: The current implementation is for educational purposes
5. **Firewall Rules**: Restrict access to trusted IPs in production environments

---

## 🚀 Production Deployment Tips

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  dns-ai-resolver:
    build: .
    container_name: dnsai
    ports:
      - "5353:5353/udp"
    env_file:
      - .env
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run with:
```bash
docker-compose up -d
```

### Monitoring and Logging

```bash
# View logs
docker-compose logs -f

# Check resource usage
docker stats dnsai
```

---

## 🧩 License

MIT License — for learning and non-commercial educational use.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Ideas for Enhancement
- Add caching layer for repeated queries
- Implement rate limiting
- Support for multiple AI models
- Web interface for management
- Prometheus metrics export
- DNS-over-HTTPS (DoH) support

---

## 📚 Additional Resources

- [Perplexity API Documentation](https://docs.perplexity.ai/)
- [dnslib Documentation](https://pypi.org/project/dnslib/)
- [Docker Documentation](https://docs.docker.com/)
- [DNS Protocol RFC](https://datatracker.ietf.org/doc/html/rfc1035)

---

## 💬 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review container logs: `docker logs dnsai`
3. Open an issue on GitHub

---

**Happy DNS querying with AI! 🎉**
