import asyncio
import random
import ssl
import json
import time
import uuid
import requests
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Daftar untuk melacak proxy yang aktif
active_proxies = []

# Menetapkan user_id secara tetap
USER_ID = '2pLeYTtCE59OKfcTtENTDS2WdiJ'  # Ganti dengan user ID yang diinginkan

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Menggunakan proxy: {socks5_proxy}, device_id: {device_id}")
    
    # Menambahkan proxy ke daftar proxy aktif
    active_proxies.append(socks5_proxy)

    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            # Membangun koneksi WebSocket
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:

                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)

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
                                "version": "4.29.0",
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))

                    else:
                        # Pesan yang tidak terduga, hapus proxy
                        logger.warning(f"Pesan tak terduga: {message}. Menghapus proxy {socks5_proxy}")
                        remove_proxy(socks5_proxy)
                        break

        except Exception as e:
            logger.error(f"Terjadi kesalahan dengan proxy {socks5_proxy}: {e}")
            remove_proxy(socks5_proxy)
            break

def remove_proxy(proxy):
    # Menghapus proxy dari daftar proxy aktif
    if proxy in active_proxies:
        active_proxies.remove(proxy)
        logger.info(f"Proxy {proxy} dihapus dari proxy aktif.")

async def main(user_id):
    # Ambil daftar proxy dari API
    r = requests.get(
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=jp,us,de&protocol=http,socks5&proxy_format=protocolipport&format=text",
        stream=True
    )
    if r.status_code == 200:
        with open('auto_proxies.txt', 'wb') as f:
            for chunk in r:
                f.write(chunk)
        with open('auto_proxies.txt', 'r') as file:
            auto_proxy_list = file.read().splitlines()

    tasks = [asyncio.ensure_future(connect_to_wss(i, user_id)) for i in auto_proxy_list]
    await asyncio.gather(*tasks)

async def restart_script(user_id):
    restart_time = 10 * 60  # 10 menit dalam detik

    while True:
        try:
            # Jalankan logika utama
            logger.info("Memulai siklus WebSocket baru...")
            await main(user_id)
            
            # Setelah 10 menit, restart script
            logger.info(f"Menunggu {restart_time / 60} menit sebelum menjalankan ulang script...")
            await asyncio.sleep(restart_time)  # Tunggu selama 10 menit sebelum restart
        except Exception as e:
            logger.error(f"Terjadi kesalahan: {e}")
            # Jika terjadi kesalahan, restart langsung
            logger.info(f"Melakukan restart segera karena kesalahan.")
            await asyncio.sleep(restart_time)  # Menunggu 10 menit sebelum memulai ulang jika ada kesalahan

if __name__ == '__main__':
    # Tidak perlu input user_id lagi karena sudah tetap
    logger.info(f"User ID yang digunakan: {USER_ID}")
    asyncio.run(restart_script(USER_ID))
