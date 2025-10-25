# 🧩 DNS-AI Resolver (Perplexity + Python)

This project lets you **chat with an AI model through DNS TXT queries**, even when normal internet (HTTP/HTTPS) is blocked.  
It uses Python, the `dnslib` package, and the **Perplexity AI API**.

---

## ⚙️ How It Works
1. A DNS server listens on UDP port `5353` (you can later use 53 with root privileges).
2. Each DNS query (e.g., `dig @localhost -p 5353 what-is-future-of-ai TXT +short`) is treated as a prompt.
3. The server sends the query to the **Perplexity AI API** using your API key.
4. The model’s short reply is returned as a **DNS TXT record**.

---

## 🧰 Requirements
- Python 3.8+
- `pip install dnslib requests`  
- A valid **Perplexity API key**

---

## 🚀 Usage

1. Clone this repository or copy the files.
2. Edit `dns_ai_resolver.py` and replace:

   ```python
   PPLX_API_KEY = "YOUR_PERPLEXITY_API_KEY"
   ```

3. Run the DNS server:

   ```bash
   python dns_ai_resolver.py
   ```

4. Query the AI through DNS:

   ```bash
   dig @127.0.0.1 -p 5353 what-is-future-of-ai TXT +short
   ```

   You’ll get a short text response from Perplexity!

---

## 🧠 Notes
- The **model** used: `sonar`
- DNS TXT record size is limited (~200 chars).  
- For production or remote testing, open UDP port 53 and use your public IP or domain.

---

## 🪶 Example Output

```bash
$ dig @127.0.0.1 -p 5353 what-is-future-of-ai TXT +short
"AI will continue to shape automation, science, and creativity in the next decade."
```

---

## 🧩 License
MIT License — for learning and non-commercial educational use.
