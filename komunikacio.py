import requests
import threading
import asyncio
import websockets

class Brain:
    def __init__(self, name: str):
        self.API_URL = "http://127.0.0.1:8000"
        self.name = name
        self.id = self.name_to_id()
        self.messenges = []
        self.friend = []
        self.ws_szal = None
        self.aktiv_ws_chat_id = None
        self.chat_ws_szal = None
        self.user_ws_szal = None

    def name_to_id(self):
        try:
            response = requests.get(f"{self.API_URL}/users/by-name/{self.name}")
            if response.status_code == 200:
                return response.json()["id"]
            else:
                raise Exception(f"Szerver hiba: {response.status_code}")
        except requests.exceptions.ConnectionError:
            raise Exception("Nem sikerült csatlakozni a szerverhez! Fut a szerver?")

    def uzenetek_betoltese(self, chat_id: int):
        try:
            adatok = {"user_id": self.id, "chat_id": chat_id}
            response = requests.get(f"{self.API_URL}/chats/{chat_id}/messages/", params=adatok)
            if response.status_code == 200:
                uzenetek = response.json()
                self.messenges = [
                    {
                        "id": msg["id"],
                        "created_at": msg["created_at"],
                        "name": msg["name"],
                        "chat_id": msg["chat_id"],
                        "text": msg["text"],
                    }
                    for msg in uzenetek
                ]
                return self.messenges
            else:
                raise Exception(f"Szerver hiba: {response.status_code}")
        except requests.exceptions.ConnectionError:
            raise Exception("Nem sikerült csatlakozni a szerverhez!")

    def uzenet_kuldese(self, messenge: str, chat_id: int):
        adatok = {"name": self.name, "chat_id": chat_id, "text": messenge}
        try:
            response = requests.post(f"{self.API_URL}/messages/", json=adatok)
            if response.status_code == 200:
                return True
            else:
                hiba_det = response.json().get("detail", "Ismeretlen hiba")
                raise Exception(f"Sikertelen küldés: {hiba_det}")
        except requests.exceptions.ConnectionError:
            raise Exception("Nem sikerült csatlakozni a szerverhez!")

    def user_chats(self):
        try:
            response = requests.get(f"/chats/")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as ex:
            print(f"Hiba a chatek betöltésekor: {ex}")
            return []

    def create_chat(self, chat_name:str):
        try:
            adatok = {"name": chat_name}
            response = requests.get(f"/chats/")





    def chat_ws_inditasa(self, chat_id: int, root, uzenet_frissito_cb):
        if self.aktiv_ws_chat_id == chat_id:
            return
        self.aktiv_ws_chat_id = chat_id

        def hallgato():
            async def listen():
                url = f"ws://127.0.0.1:8000/ws/{chat_id}"
                try:
                    async with websockets.connect(url) as ws:
                        while self.aktiv_ws_chat_id == chat_id:
                            await ws.recv()
                            root.after(0, lambda: uzenet_frissito_cb(chat_id))
                except Exception as e:
                    print(f"Chat WS hiba: {e}")

            asyncio.run(listen())

        self.chat_ws_szal = threading.Thread(target=hallgato, daemon=True)
        self.chat_ws_szal.start()

    # 2. FELHASZNÁLÓI ÉRTESÍTÉS HALLGATÓ (új chatekhez)
    def user_ws_inditasa(self, root, gomb_frissito_cb):
        def hallgato():
            async def listen():
                url = f"ws://127.0.0.1:8000/ws/user/{self.id}"
                try:
                    async with websockets.connect(url) as ws:
                        while True:
                            msg = await ws.recv()
                            if msg == "REFRESH_CHATS":
                                root.after(0, gomb_frissito_cb)
                except Exception as e:
                    print(f"User WS hiba: {e}")

            asyncio.run(listen())

        self.user_ws_szal = threading.Thread(target=hallgato, daemon=True)
        self.user_ws_szal.start()