import customtkinter as ctk
from threading import Thread
from reader import *

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.geometry("1000x600")
app.title("LoL Account Tool")

last_title = ""
is_loading = False
loading_step = 0
last_summary = ""

# =========================
# THREAD HELPER
# =========================

def run_thread(func):
    Thread(target=func, daemon=True).start()

# =========================
# FUNCIONES
# =========================

def show_summary():
    disable_buttons()
    set_loading(True, "Fetching account data...")

    try:
        seller = get_seller_name()
        server = get_server_region()
        level = get_summoner_level()
        rank = get_rank_info()
        placements = get_placements_info()
        champions_count = get_champions_count()
        skins_count = get_skins_count()
        blue_essence = get_blue_essence()
        orange_essence = get_orange_essence()
        chests = get_hextech_chests()
        keys = get_hextech_keys()
        refunds = get_refunds_remaining()
        can_change = can_change_name()

        champions_list = get_champions_list()
        champ_shards, skin_shards = get_champion_skins_shards_list()

        set_loading(False)

        text = f"""
{seller}
━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 Server: {server}
📈 Level: {level}
🎯 Rank: {rank}
{placements if placements else ""}

👤 Champions: {champions_count}
🎨 Skins: {skins_count}

🔵 BE: {blue_essence}
🟠 OE: {orange_essence}

📦 Chests: {chests}
🗝️ Keys: {keys}
🔙 Refunds: {refunds}

{"🔄 Can change name" if can_change else ""}
"""
        global last_summary
        last_summary = text
        output.insert("end", text)
        
        if champions_list:
            champs_text = f"\n\n📜 Champions ({len(champions_list)}):\n"
            for c in champions_list:
                champs_text += f"- {c}\n"

            last_summary += champs_text
            output.insert("end", champs_text)

        if champ_shards and len(champ_shards.splitlines()) > 1:
            output.insert("end", "\n\n" + champ_shards)

        if skin_shards and len(skin_shards.splitlines()) > 1:
            last_summary += "\n\n" + skin_shards
            output.insert("end", "\n\n" + skin_shards)

    finally:
        enable_buttons()


def generate_title_action():
    global last_title

    disable_buttons()
    set_loading(True, "Generating title...")

    try:
        server = get_server_region()
        level = get_summoner_level()
        rank = get_rank_info()
        champions_count = get_champions_count()
        skins_count = get_skins_count()
        blue_essence = get_blue_essence()
        orange_essence = get_orange_essence()

        _, skin_shards = get_champion_skins_shards_list()

        win, losses = get_rank_wins_losses()
        lp_per_win = estimate_lp_per_win(win, losses, level) if win and losses else None

        last_title = generate_title_v2(
            server=server,
            rank=rank,
            level=level,
            skins=skins_count,
            skin_shards=len(skin_shards.splitlines()) if skin_shards else 0,
            lp_per_win=lp_per_win,
            champions=champions_count,
            blue_essence=blue_essence,
            orange_essence=orange_essence
        )

        set_loading(False)

        output.insert("end", "🔥 GENERATED TITLE:\n\n")
        output.insert("end", last_title)

    finally:
        enable_buttons()


def copy_summary():
    global last_summary

    if last_summary:
        app.clipboard_clear()
        app.clipboard_append(last_summary.strip())

        copy_summary_btn.configure(text="✅ Summary Copied")
        app.after(1500, lambda: copy_summary_btn.configure(text="📋 Copy Summary"))  

def copy_title():
    global last_title

    if last_title:
        app.clipboard_clear()
        app.clipboard_append(last_title)

        copy_title_btn.configure(text="✅ Title Copied")

        app.after(1500, lambda: copy_title_btn.configure(text="🏷️ Copy Title"))


def delete_friends_action():
    output.insert("end", "\n🧹 Deleting friends...\n")
    delete_all_friends()
    output.insert("end", "✅ Done\n")


def disable_buttons():
    for b in buttons:
        b.configure(state="disabled")


def enable_buttons():
    for b in buttons:
        b.configure(state="normal")


def set_loading(state, text="Loading"):
    global is_loading, loading_step

    is_loading = state
    loading_step = 0

    if state:
        animate_loading(text)


def animate_loading(text="Loading"):
    global loading_step

    if not is_loading:
        return

    dots = "." * (loading_step % 4)
    output.delete("1.0", "end")
    output.insert("end", f"⏳ {text}{dots}")

    loading_step += 1

    app.after(400, lambda: animate_loading(text))

# =========================
# LAYOUT
# =========================

# SIDEBAR
sidebar = ctk.CTkFrame(app, width=200)
sidebar.pack(side="left", fill="y")

title_label = ctk.CTkLabel(sidebar, text="⚙️ Menu", font=("Arial", 18, "bold"))
title_label.pack(pady=20)

btn_summary = ctk.CTkButton(sidebar, text="🔍 Summary", command=lambda: run_thread(show_summary))
btn_summary.pack(pady=10, padx=10)

gen_btn = ctk.CTkButton(sidebar, text="⚡ Gen Title", command=lambda: run_thread(generate_title_action))
gen_btn.pack(pady=10, padx=10)

copy_summary_btn = ctk.CTkButton(sidebar, text="📋 Copy Summary", command=copy_summary)
copy_summary_btn.pack(pady=10, padx=10)

copy_title_btn = ctk.CTkButton(sidebar, text="🏷️ Copy Title", command=copy_title)
copy_title_btn.pack(pady=10, padx=10)

btn_delete = ctk.CTkButton(
    sidebar,
    text="🧹 Delete Friends",
    fg_color="red",
    command=lambda: run_thread(delete_friends_action)
)
btn_delete.pack(pady=10, padx=10)

# MAIN AREA
main = ctk.CTkFrame(app)
main.pack(side="right", expand=True, fill="both")

header = ctk.CTkLabel(main, text="LoL Account Manager", font=("Arial", 24, "bold"))
header.pack(pady=20)

output = ctk.CTkTextbox(main)
output.pack(expand=True, fill="both", padx=20, pady=20)

buttons = [
    btn_summary,
    gen_btn,
    copy_summary_btn,
    copy_title_btn,
    btn_delete
]

# =========================
# RUN
# =========================

app.mainloop()