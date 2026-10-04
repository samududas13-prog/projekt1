import customtkinter as ctk
from komunikacio import Brain
import os, json

root = ctk.CTk()
root.title("messenge")
root.geometry("800x600")

DATAI = os.path.join(os.path.dirname(__file__), "datai.json")

def datai_read():
    with open(DATAI, encoding="utf8") as f:
        return json.load(f)

class App:
    def __init__(self, root):
        self.root = root
        self.data = datai_read()
        self.name = self.data.get("name", "")
        self.connection = Brain(self.name)
        self.friends = self.connection.user_chats()
        

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)

        self.bal_sav = ctk.CTkScrollableFrame(self.root, fg_color="#2b2b2b")
        self.bal_sav.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.bal_sav.grid_rowconfigure(0, weight=0)
        self.bal_sav.grid_rowconfigure(1, weight=1)
        self.bal_sav.grid_columnconfigure(0, weight=1)

        self.bal_up_buttons = ctk.CTkFrame(self.bal_sav, fg_color="#2b2b2b")
        self.bal_up_buttons.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.chat_button_sav = ctk.CTkScrollableFrame(self.bal_sav, fg_color="#2b2b2b")
        self.chat_button_sav.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.jobb_sav = ctk.CTkFrame(self.root, fg_color="#1a2332")
        self.jobb_sav.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.jobb_sav.grid_rowconfigure(0, weight=1)
        self.jobb_sav.grid_rowconfigure(1, weight=0)
        self.jobb_sav.grid_columnconfigure(0, weight=1)

        self.uzenet_keret = ctk.CTkScrollableFrame(self.jobb_sav, fg_color="transparent")
        self.uzenet_keret.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.label2 = []

        self.beviteli_mezo = ctk.CTkTextbox(self.jobb_sav, height=50, fg_color="#C329D1")
        self.beviteli_mezo.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.beviteli_mezo.bind("<Return>", self.enter_kezelo)

        
        
        
        
        if self.friends:
            self.chat_id = self.friends[0]["id"]
            self.messenges = self.connection.uzenetek_betoltese(self.chat_id)
            self.jobb_igazitas()
            self.connection.chat_ws_inditasa(self.chat_id, self.root, self.jobb_oldal_frissites)
        else:
            self.chat_id = None
            self.messenges = []

        self.connection.user_ws_inditasa(self.root, self.your_chats_button)
        self.your_chats_button()



    def your_chats_button(self):
        for child in self.chat_button_sav.winfo_children():
            child.destroy()
        self.friends = self.connection.user_chats()
        for i in self.friends:
            gomb = ctk.CTkButton(self.chat_button_sav, text=i["name"], command=lambda cid=i["id"]: self.jobb_oldal_frissites(cid))
            gomb.pack(pady=10, padx=10, anchor="w")

    def jobb_oldal_frissites(self, chat_id: int):
        self.messenges = self.connection.uzenetek_betoltese(chat_id)
        self.chat_id = chat_id
        self.jobb_igazitas()
        self.connection.chat_ws_inditasa(chat_id, self.root, self.jobb_oldal_frissites)

    def jobb_igazitas(self):
        for j in self.label2:
            j.destroy()
        self.label2.clear()

        szovegdoboz_szin = "#FD5E5E"
        sajat_szov_doboz_szin = "#765EFD"

        for i in self.messenges:
            if i["name"] != self.name:
                label = ctk.CTkLabel(
                    self.uzenet_keret, text=i["text"], 
                    fg_color=szovegdoboz_szin, corner_radius=10, 
                    border_width=10, border_color=szovegdoboz_szin
                )
                label.pack(pady=10, padx=10, anchor="w")
            else:
                label = ctk.CTkLabel(
                    self.uzenet_keret, text=i["text"], 
                    fg_color=sajat_szov_doboz_szin, corner_radius=10, 
                    border_width=10, border_color=sajat_szov_doboz_szin
                )
                label.pack(pady=10, padx=10, anchor="e")
            self.label2.append(label)

        self.root.update_idletasks()
        self.uzenet_keret._parent_canvas.yview_moveto(1.0)

    def enter_kezelo(self, event):
        if event.state & 0x0001:
            return  

        szoveg = self.beviteli_mezo.get("1.0", "end").strip()
        if szoveg:
            self.connection.uzenet_kuldese(szoveg, self.chat_id)
            self.beviteli_mezo.delete("1.0", "end")
            self.jobb_oldal_frissites(self.chat_id)

        return "break"

ap = App(root)
root.mainloop()