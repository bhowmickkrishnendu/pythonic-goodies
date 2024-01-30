import asyncio
import websockets

async def test_websocket(url):
    try:
        async with websockets.connect(url) as websocket:
            print(f"Connected to {url}")
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")
    except websockets.exceptions.InvalidURI:
        print(f"Invalid WebSocket URI: {url}")
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    url = input("Enter WebSocket URL: ")
    asyncio.run(test_websocket(url))