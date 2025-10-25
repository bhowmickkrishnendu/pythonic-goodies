from dnslib import DNSRecord, QTYPE, RR, TXT
from dnslib.server import DNSServer
import requests, json, time, os
from dotenv import load_dotenv

# Load .env file
load_dotenv()
PPLX_API_KEY = os.getenv("PPLX_API_KEY")

if not PPLX_API_KEY:
    raise ValueError("Missing PPLX_API_KEY in .env file")

def ask_perplexity(prompt):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code != 200:
            print("API Error:", r.status_code, r.text)
            return f"error: {r.status_code}"

        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"][:200]
        elif "output_text" in data:
            return data["output_text"][:200]
        else:
            return str(data)[:200]

    except Exception as e:
        return f"error: {e}"

class DNSAIResolver:
    def resolve(self, request, handler):
        qname = str(request.q.qname).rstrip('.')
        question = qname.replace('-', ' ').split('.')[0]
        print(f"Received query: {question}")
        answer = ask_perplexity(question)
        reply = request.reply()
        reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.TXT, rdata=TXT(answer), ttl=30))
        return reply

if __name__ == "__main__":
    resolver = DNSAIResolver()
    server = DNSServer(resolver, port=5353, address="0.0.0.0", tcp=False)
    server.start_thread()
    print("DNS AI Server running on UDP port 5353...")
    print("Use: dig @localhost -p 5353 what-is-future-of-ai TXT +short")
    while True:
        time.sleep(1)
