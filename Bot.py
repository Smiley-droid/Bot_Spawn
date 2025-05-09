import discord
from discord.ext import commands, tasks
import asyncio
import os
import re
from datetime import datetime
import json

# === CHARGEMENT DE LA CONFIGURATION ===
with open("config.json", "r") as f:
    config = json.load(f)

TOKEN = config["TOKEN"]
CHANNEL_ID = config["CHANNEL_ID"]
WHISPER_CHANNEL_ID = config["WHISPER_CHANNEL_ID"]
VISUAL_ALERT_CHANNEL_ID = config["VISUAL_ALERT_CHANNEL_ID"]
LOG_PATH = config["LOG_PATH"]
WHITELIST_KEYWORDS = config["WHITELIST_KEYWORDS"]
IGNORED_KEYWORDS = config["IGNORED_KEYWORDS"]


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# === COULEURS PAR TYPE D'ÉVÉNEMENT ===
def detect_event_color(message, is_whisper=False, whisper_type=None):
    lower = message.lower()

    if is_whisper:
        return 0x9B59B6 if whisper_type == "sent" else 0x00BFFF

    if "joined the game" in lower:
        return 0x00FF19  # Vert
    elif "left the game" in lower:
        return 0x616161  # Gris foncé
    elif any(w in lower for w in [
        "was slain", "was shot", "fell", "tried to swim", "blew up",
        "drowned", "burnt", "was killed", "killed by", "was doomed",
        "burned", "was blown"
    ]):
        return 0xFF0015  # Rouge (morts)
    elif any(a in lower for a in [
        "has made the advancement", "has completed the challenge", "has reached the goal"
    ]):
        return 0xFF6800  # Orange (avancement)
    elif "<" in message and ">" in message:
        return 0x003BFF  # Bleu foncé (chat)
    else:
        return 0x00FF88  # Par défaut

# === ENVOI DES EMBEDS ===
async def send_minecraft_embed(channel, pseudo, message, color=None):
    avatar_url = f"https://minotar.net/avatar/{pseudo}/64"
    embed = discord.Embed(description=message, color=color if color else detect_event_color(message))
    embed.set_author(name=pseudo, icon_url=avatar_url)
    await channel.send(embed=embed)

@tasks.loop(seconds=0.5)
async def monitor_log():
    main_channel = bot.get_channel(CHANNEL_ID)
    whisper_channel = bot.get_channel(WHISPER_CHANNEL_ID)
    visual_alert_channel = bot.get_channel(VISUAL_ALERT_CHANNEL_ID)

    if not all([main_channel, whisper_channel, visual_alert_channel]):
        print("❌ Un ou plusieurs salons sont introuvables.")
        return

    def open_log():
        f = open(LOG_PATH, "r", encoding="utf-8-sig", errors="replace")
        f.seek(0, os.SEEK_END)
        return f, os.fstat(f.fileno()).st_ino

    log_file, current_inode = open_log()

    while True:
        try:
            new_inode = os.stat(LOG_PATH).st_ino
            current_time = datetime.now().strftime("%H:%M:%S")

            if new_inode != current_inode or current_time == "00:00:01":
                print(f"🔁 Réouverture du log (inode changé ou minuit)")
                log_file.close()
                log_file, current_inode = open_log()
        except Exception as e:
            print("⚠️ Erreur inode :", e)

        line = log_file.readline()
        if not line:
            await asyncio.sleep(0.1)
            continue

        if "[CHAT]" not in line:
            continue

        message = line.strip().split("[CHAT]")[-1].strip()

        try:
            if "whispers to you:" in message:
                pseudo, texte = message.split("whispers to you:")
                await send_minecraft_embed(whisper_channel, pseudo.strip(), texte.strip(), color=0x00BFFF)
                continue

            if message.lower().startswith("you whisper to "):
                content = message[len("You whisper to "):]
                destinataire, texte = content.split(":", 1)
                msg = f"You to {destinataire.strip()}: {texte.strip()}"
                await send_minecraft_embed(whisper_channel, destinataire.strip(), msg, color=0x9B59B6)
                continue

            if "[Meteor]" in message and "has entered your visual range" in message:
                pseudo = message.split("[Meteor]")[-1].split("has entered")[0].strip()
                alert_message = f"🚨 **{pseudo} est au spawn !**"
                await send_minecraft_embed(visual_alert_channel, pseudo, alert_message, color=0xFF0000)
                continue

            match = re.match(r"^<([^<>]+)> (.+)", message)
            if match:
                pseudo, texte = match.groups()
                full_message = f"<{pseudo}> {texte}"
                await send_minecraft_embed(main_channel, pseudo.strip(), texte.strip(), color=detect_event_color(full_message))
                continue

            elif any(keyword in message for keyword in [
                "joined the game", "left the game", "was slain", "has made the advancement",
                "has completed the challenge", "was shot", "fell", "tried to swim", "blew up",
                "drowned", "burnt", "was killed", "killed by", "was doomed", "burned", "was blown"
            ]):
                mots = message.split()
                pseudo = mots[0] if mots else "Serveur"
                await send_minecraft_embed(main_channel, pseudo, message, color=detect_event_color(message))
                continue

            if not any(keyword.lower() in message.lower() for keyword in WHITELIST_KEYWORDS):
                await send_minecraft_embed(main_channel, "Serveur", message, color=detect_event_color(message))

        except Exception as e:
            print(f"❌ Erreur traitement message : {e}")

# === DÉMARRAGE DU BOT ===
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    monitor_log.start()

bot.run(TOKEN)
