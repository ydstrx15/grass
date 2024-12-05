import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent


async def connect_to_wss(socks5_proxy, user_id):
    """
    Menghubungkan ke server WebSocket melalui SOCKS5 proxy.

    Args:
        socks5_proxy (str): Alamat proxy SOCKS5.
        user_id (str): ID pengguna yang akan diautentikasi.
    """
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Device ID: {device_id}")
    
    # Membuat User-Agent khusus
    user_agent = UserAgent(os='mac', platforms='pc', browsers='brave')
    random_user_agent = user_agent.random
    
    while True:
        try:
            await asyncio.sleep(random.uniform(0.1, 1.0))  # Jeda acak untuk menghindari beban berlebih
            custom_headers = {
                "User-Agent": random_user_agent,
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Pilihan URI server WebSocket
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            
            # Membuka koneksi WebSocket
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    """Mengirimkan pesan PING setiap 5 detik."""
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}}
                        )
                        logger.debug(f"Sending PING: {send_message}")
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                asyncio.create_task(send_ping())  # Memulai task pengiriman PING

                while True:
                    response = await websocket.recv()  # Menunggu pesan dari server
                    message = json.loads(response)
                    logger.info(f"Received: {message}")

                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "desktop",
                                "version": "4.28.1",
                            }
                        }
                        logger.debug(f"Sending AUTH response: {auth_response}")
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(f"Sending PONG response: {pong_response}")
                        await websocket.send(json.dumps(pong_response))

        except Exception as e:
            logger.error(f"Error with proxy {socks5_proxy}: {e}")
            await asyncio.sleep(5)  # Jeda untuk menghindari loop terus-menerus


async def main():
    """
    Fungsi utama untuk membaca proxy dari file dan memulai koneksi WebSocket.
    """
    _user_id = input("Please Enter your user ID: ").strip()
    if not _user_id:
        logger.error("User ID cannot be empty.")
        return

    try:
        with open('local_proxies.txt', 'r') as file:
            local_proxies = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logger.error("File 'local_proxies.txt' not found. Please create it and add proxy addresses.")
        return

    if not local_proxies:
        logger.error("No proxies found in 'local_proxies.txt'. Please add valid proxy addresses.")
        return

    # Membuat task untuk setiap proxy
    tasks = [asyncio.create_task(connect_to_wss(proxy, _user_id)) for proxy in local_proxies]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    logger.info("Starting WebSocket connection...")
    asyncio.run(main())