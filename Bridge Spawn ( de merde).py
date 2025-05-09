import discord
from discord.ext import commands, tasks
import asyncio
import os
import re

# === CONFIGURATION ===
TOKEN = "ton token"  # Remplace avec ton vrai token
CHANNEL_ID = 1368146695098994810         # Salon principal (chat global, morts, succès)
WHISPER_CHANNEL_ID = 1368330872779964497 # Salon spécial pour les messages privés

LOG_PATH = r"C:\Users\nom\AppData\Roaming\PrismLauncher\instances\1.20.1\minecraft\logs\latest.log"
IGNORED_KEYWORDS = ["[Meteor]", "fly", "cheat"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# === COULEUR PAR ÉVÉNEMENT ===
def detect_event_color(message, is_whisper=False, whisper_type=None):
    lower = message.lower()

    # 🎯 Whispers
    if is_whisper:
        if whisper_type == "sent":
            return 0x9B59B6  # Violet foncé pour messages envoyés
        else:
            return 0x00BFFF  # Cyan pour messages reçus

    # ✅ Connexion
    if "joined the game" in lower:
        return 0x1ABC9C  # Turquoise

    # ⬅️ Déconnexion
    elif "left the game" in lower:
        return 0x747F8D  # Gris

    # 💀 Morts
    elif any(word in lower for word in [
        "was slain", "was shot", "fell", "tried to swim", "blew up",
        "drowned", "burnt", "was killed", "killed by"
    ]):
        return 0xED4245  # Rouge

    # 🏆 Achievements
    elif "has made the advancement" in lower or "has completed the challenge" in lower:
        return 0xFAA61A  # Orange

    # 💬 Chat public
    elif "<" in message and ">" in message:
        return 0x3498DB  # Bleu clair

    # 🌐 Autres
    else:
        return 0x00FF88  # Vert fluo par défaut

# === ENVOI EMBED DISCORD ===
async def send_minecraft_embed(channel, pseudo, message, is_whisper=False, whisper_type=None):
    avatar_url = f"https://minotar.net/avatar/{pseudo}/64"
    color = detect_event_color(message, is_whisper=is_whisper, whisper_type=whisper_type)
    embed = discord.Embed(description=message, color=color)
    embed.set_author(name=pseudo, icon_url=avatar_url)
    await channel.send(embed=embed)

# === TÂCHE : MONITORING DES LOGS ===
@tasks.loop(seconds=0.5)
async def monitor_log():
    main_channel = bot.get_channel(CHANNEL_ID)
    whisper_channel = bot.get_channel(WHISPER_CHANNEL_ID)

    if not main_channel or not whisper_channel:
        print("❌ Un ou plusieurs salons sont introuvables.")
        return

    with open(LOG_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue

            if "[CHAT]" in line:
                message = line.strip().split("[CHAT]")[-1].strip()
                if any(word.lower() in message.lower() for word in IGNORED_KEYWORDS):
                    continue

                # 🔒 Whisper reçu
                if "whispers to you:" in message:
                    try:
                        parts = message.split("whispers to you:")
                        pseudo = parts[0].strip()
                        texte = parts[1].strip()
                        await send_minecraft_embed(whisper_channel, pseudo, texte, is_whisper=True, whisper_type="received")
                        continue
                    except Exception as e:
                        print("⚠️ Erreur whisper reçu :", e)

                # 🔐 Whisper envoyé
                if message.lower().startswith("you whisper to "):
                    try:
                        content = message[len("You whisper to "):]
                        if ":" in content:
                            destinataire, texte = content.split(":", 1)
                            destinataire = destinataire.strip()
                            texte = texte.strip()
                            pseudo = destinataire
                            msg = f"You to {destinataire}: {texte}"
                            await send_minecraft_embed(whisper_channel, pseudo, msg, is_whisper=True, whisper_type="sent")
                        else:
                            print("⚠️ Message whisper mal formé :", content)
                        continue
                    except Exception as e:
                        print("⚠️ Erreur whisper envoyé :", e)

                # 💬 Chat normal (format Minecraft <pseudo> message)
                match = re.match(r"^<([^<>]+)> (.+)", message)
                if match:
                    pseudo = match.group(1).strip()
                    texte = match.group(2).strip()
                    await send_minecraft_embed(main_channel, pseudo, texte)
                    continue


                # 🎯 Événements (morts, reco, succès)
                elif any(keyword in message for keyword in [
                    "joined the game", "left the game", "was slain", "has made the advancement",
                    "has completed the challenge", "was shot", "fell", "tried to swim", "blew up", "drowned",
                    "burnt", "was killed", "killed by"
                ]):
                    mots = message.split()
                    pseudo = mots[0] if mots else "Serveur"
                    await send_minecraft_embed(main_channel, pseudo, message)
                    continue

                # 💡 Autres
                else:
                    await send_minecraft_embed(main_channel, "Serveur", message)

# === BOT READY ===
@bot.event
async def on_ready():
    print(f"✅ Connecté à Discord en tant que {bot.user}")
    monitor_log.start()

# === START ===
bot.run(TOKEN)
