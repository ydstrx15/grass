import subprocess
import time
import sys
import asyncio
import random
import ssl
import json
import uuid
import requests
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Daftar untuk melacak proxy yang aktif
active_proxies = []

# Gunakan `user_id` tetap
USER_ID = '2pLeYTtCE59OKfcTtENTDS2WdiJ'  # Ganti dengan ID Anda


async def connect_to_wss(socks5_proxy, user_id):
    # Membuat User-Agent acak
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Menggunakan proxy: {socks5_proxy}, device_id: {device_id}")
    
    # Menambahkan proxy ke daftar proxy aktif
    active_proxies.append(socks5_proxy)

    while True:
        try:
            # Menunggu jeda waktu acak sebelum melanjutkan
            await asyncio.sleep(random.randint(1, 10) / 10)
            
            # Header kustom untuk koneksi WebSocket
            custom_headers = {
                "User-Agent": random_user_agent,
            }
            # Konfigurasi SSL untuk mengabaikan sertifikat
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Daftar URI WebSocket yang digunakan
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            # Membuat koneksi WebSocket melalui proxy
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:

                # Fungsi untuk mengirim PING setiap 5 detik
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                # Loop untuk menerima dan memproses pesan dari WebSocket
                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)

                    if message.get("action") == "AUTH":
                        # Respon untuk pesan AUTH
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
                        # Respon untuk pesan PONG
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))

                    else:
                        # Jika menerima pesan tak terduga, hapus proxy
                        logger.warning(f"Pesan tak terduga: {message}. Menghapus proxy {socks5_proxy}")
                        remove_proxy(socks5_proxy)
                        break

        except Exception as e:
            # Tangani error dan hapus proxy dari daftar aktif
            logger.error(f"Exception dengan proxy {socks5_proxy}: {e}")
            remove_proxy(socks5_proxy)
            break


def remove_proxy(proxy):
    # Hapus proxy dari daftar proxy aktif
    if proxy in active_proxies:
        active_proxies.remove(proxy)
        logger.info(f"Proxy {proxy} dihapus dari daftar aktif.")


async def websocket_main():
    # Menggunakan USER_ID yang telah didefinisikan sebelumnya
    user_id = USER_ID
    print(f"User ID yang digunakan: {user_id}")
    
    # Mengambil daftar proxy dari API
    r = requests.get(
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text",
        stream=True
    )
    if r.status_code == 200:
        # Menyimpan daftar proxy ke file
        with open('auto_proxies.txt', 'wb') as f:
            for chunk in r:
                f.write(chunk)
        with open('auto_proxies.txt', 'r') as file:
            auto_proxy_list = file.read().splitlines()

    # Membuat tugas untuk setiap proxy
    tasks = [asyncio.ensure_future(connect_to_wss(i, user_id)) for i in auto_proxy_list]
    await asyncio.gather(*tasks)


def run_websocket_script():
    """Fungsi untuk menjalankan script WebSocket dengan subprocess."""
    try:
        process = subprocess.Popen([sys.executable, __file__, "--child"])
        print(f"Script WebSocket dimulai dengan PID: {process.pid}")
        return process
    except Exception as e:
        print(f"Error menjalankan script WebSocket: {e}")
        return None


def main():
    if "--child" in sys.argv:
        # Jika skrip dijalankan sebagai child process, jalankan fungsi WebSocket
        asyncio.run(websocket_main())
        return

    print("Script WebSocket dengan Auto-Restart")
    print("Pastikan script ini berada di folder yang sama dengan dependensinya.")
    restart_time = int(input("Masukkan waktu restart dalam menit (min 1): "))

    while True:
        # Menjalankan script WebSocket
        process = run_websocket_script()
        if process:
            try:
                # Tunggu selama waktu restart yang ditentukan
                time.sleep(restart_time * 60)
            finally:
                # Menghentikan dan me-restart proses WebSocket
                print(f"Menghentikan script WebSocket setelah {restart_time} menit.")
                process.terminate()
                process.wait()
        else:
            print("Gagal memulai script WebSocket, mencoba lagi dalam 10 detik...")
            time.sleep(10)


if __name__ == "__main__":
    main()