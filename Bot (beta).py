import discord
from discord.ext import commands, tasks
import asyncio
import os
import re

# === CONFIGURATION ===
TOKEN = "Votre token"  # Ton token bot Discord
CHANNEL_ID = 1368146695098994810  # ID du salon principal (chat global, morts, succès)
WHISPER_CHANNEL_ID = 1368330872779964497  # ID du salon spécial pour les messages privés
VISUAL_ALERT_CHANNEL_ID = 1368146765123031131  # 🔴 Ton salon Discord pour les alertes de champ visuel

LOG_PATH = r"C:\Users\Administrateur\AppData\Roaming\PrismLauncher\instances\1.20.1\minecraft\logs\latest.log"
IGNORED_KEYWORDS = ["fly", "cheat"]  # Supprimé "[Meteor]" ici car on l'utilise maintenant
WHITELIST_KEYWORDS = ["[Meteor]"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# === COULEUR PAR ÉVÉNEMENT ===
def detect_event_color(message, is_whisper=False, whisper_type=None):
    lower = message.lower()

    if is_whisper:
        return 0x9B59B6 if whisper_type == "sent" else 0x00BFFF

    if "joined the game" in lower:
        return 0x1ABC9C  # Connexion (turquoise)
    elif "left the game" in lower:
        return 0x747F8D  # Déconnexion (gris)
    elif any(w in lower for w in ["was slain", "was shot", "fell", "tried to swim", "blew up", "drowned", "burnt", "was killed", "killed by"]):
        return 0xED4245  # Morts (rouge)
    elif "has made the advancement" in lower or "has completed the challenge" in lower:
        return 0xFAA61A  # Succès (orange)
    elif "<" in message and ">" in message:
        return 0x3498DB  # Chat public (bleu)
    else:
        return 0x00FF88  # Autres (vert fluo)

# === ENVOI EMBED ===
async def send_minecraft_embed(channel, pseudo, message, color=None):
    avatar_url = f"https://minotar.net/avatar/{pseudo}/64"
    embed = discord.Embed(description=message, color=color if color else detect_event_color(message))
    embed.set_author(name=pseudo, icon_url=avatar_url)
    await channel.send(embed=embed)

# === TÂCHE PRINCIPALE ===
@tasks.loop(seconds=0.5)
async def monitor_log():
    main_channel = bot.get_channel(CHANNEL_ID)
    whisper_channel = bot.get_channel(WHISPER_CHANNEL_ID)
    visual_alert_channel = bot.get_channel(VISUAL_ALERT_CHANNEL_ID)

    if not all([main_channel, whisper_channel, visual_alert_channel]):
        print("❌ Un ou plusieurs salons sont introuvables.")
        return

    with open(LOG_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue

            if "[CHAT]" not in line:
                continue

            message = line.strip().split("[CHAT]")[-1].strip()

            # 💬 Whisper reçu
            if "whispers to you:" in message:
                try:
                    pseudo, texte = message.split("whispers to you:")
                    await send_minecraft_embed(whisper_channel, pseudo.strip(), texte.strip(), color=0x00BFFF)
                    continue
                except Exception as e:
                    print("⚠️ Erreur whisper reçu :", e)

            # 💬 Whisper envoyé
            if message.lower().startswith("you whisper to "):
                try:
                    content = message[len("You whisper to "):]
                    destinataire, texte = content.split(":", 1)
                    msg = f"You to {destinataire.strip()}: {texte.strip()}"
                    await send_minecraft_embed(whisper_channel, destinataire.strip(), msg, color=0x9B59B6)
                    continue
                except Exception as e:
                    print("⚠️ Erreur whisper envoyé :", e)

            # 🚨 Détection METEOR visual range
            if "[Meteor]" in message and "has entered your visual range" in message:
                try:
                    pseudo = message.split("[Meteor]")[-1].split("has entered")[0].strip()
                    alert_message = f"🚨 **{pseudo} est au spawn !**"
                    await send_minecraft_embed(visual_alert_channel, pseudo, alert_message, color=0xFF0000)
                    continue
                except Exception as e:
                    print("⚠️ Erreur Meteor entered:", e)

            # 🟨 Chat normal
            match = re.match(r"^<([^<>]+)> (.+)", message)
            if match:
                pseudo, texte = match.groups()
                await send_minecraft_embed(main_channel, pseudo.strip(), texte.strip())
                continue

            # 🎯 Événements système
            elif any(keyword in message for keyword in [
                "joined the game", "left the game", "was slain", "has made the advancement",
                "has completed the challenge", "was shot", "fell", "tried to swim", "blew up", "drowned",
                "burnt", "was killed", "killed by"
            ]):
                mots = message.split()
                pseudo = mots[0] if mots else "Serveur"
                await send_minecraft_embed(main_channel, pseudo, message)
                continue

            # 💡 Autres messages
            # 🔒 Vérifie si le message est whitelisté
            if not any(keyword.lower() in message.lower() for keyword in WHITELIST_KEYWORDS):
                await send_minecraft_embed(main_channel, "Serveur", message)


# === LANCEMENT DU BOT ===
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    monitor_log.start()

bot.run(TOKEN)
