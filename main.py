import discord, os, base64, hashlib, time, re, random, string, asyncio, yt_dlp
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("TOKEN")

SCAN_CHANNEL_ID = 1469740150522380299
START_TIME = time.time()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot Ready!")

# ================= MENU =================
@bot.tree.command(name="menu")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Tatang SA-MP • Main Menu",
        description=
        "**AI & Security Tools Bot**\n\n"
        "🧠 **AI Commands**\n"
        "`/ai` `/askcode` `/summarize` `/translate`\n\n"
        "🔐 **Obfuscation**\n"
        "`/obf`\n\n"
        "📥 **Downloader**\n"
        "`/ytmp3` `/ytmp4`\n\n"
        "🛡 **Security Scanner**\n"
        "Upload file di channel scan\n\n"
        "🛠 **Tools**\n"
        "`/encode` `/decode` `/hash` `/ping` `/uptime`\n",
        color=0x00ffcc
    )
    embed.set_footer(text="Tatang SA-MP • AI & Security Tools")
    await interaction.response.send_message(embed=embed)

# ================= AI =================
@bot.tree.command(name="ai")
async def ai(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"🤖 AI Response:\n{text[::-1]}")

@bot.tree.command(name="askcode")
async def askcode(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(f"💻 Code AI:\n{question}")

@bot.tree.command(name="summarize")
async def summarize(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(text[:200] + "...")

@bot.tree.command(name="translate")
async def translate(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"🌐 Translate:\n{text}")

# ================= TOOLS =================
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="uptime")
async def uptime(interaction: discord.Interaction):
    seconds = int(time.time() - START_TIME)
    await interaction.response.send_message(f"⏱ Uptime: {seconds} seconds")

@bot.tree.command(name="encode")
async def encode(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(base64.b64encode(text.encode()).decode())

@bot.tree.command(name="decode")
async def decode(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(base64.b64decode(text.encode()).decode())

@bot.tree.command(name="hash")
async def hash_cmd(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(hashlib.sha256(text.encode()).hexdigest())

# ================= YOUTUBE =================
async def download_youtube(url, audio=False):
    ydl_opts = {
        'format': 'bestaudio/best' if audio else 'best',
        'outtmpl': 'video.%(ext)s'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

@bot.tree.command(name="ytmp3")
async def ytmp3(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    await download_youtube(url, audio=True)
    await interaction.followup.send(file=discord.File("video.webm"))

@bot.tree.command(name="ytmp4")
async def ytmp4(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    await download_youtube(url)
    await interaction.followup.send(file=discord.File("video.mp4"))

# ================= OBFUSCATION =================
def random_string():
    return ''.join(random.choice(string.ascii_letters) for _ in range(8))

def obf_low(code):
    return base64.b64encode(code.encode()).decode()

def obf_medium(code):
    code = re.sub(r"\b(local|function)\s+(\w+)", lambda m: m.group(1)+" "+random_string(), code)
    return base64.b64encode(code.encode()).decode()

def obf_hard(code):
    key = random.randint(5, 20)
    encrypted = "".join(chr(ord(c) ^ key) for c in code)
    junk = "-- Anti Decompile\n" * 5
    return junk + base64.b64encode(encrypted.encode()).decode()

@bot.tree.command(name="obf")
async def obf(interaction: discord.Interaction, file: discord.Attachment, level: str):
    content = (await file.read()).decode(errors="ignore")
    if level.lower() == "low":
        result = obf_low(content)
    elif level.lower() == "medium":
        result = obf_medium(content)
    else:
        result = obf_hard(content)

    fname = f"obf_{level}_{file.filename}"
    with open(fname, "w") as f:
        f.write(result)

    await interaction.response.send_message(file=discord.File(fname))

# ================= SECURITY SCAN =================
@bot.event
async def on_message(message):
    if message.channel.id != SCAN_CHANNEL_ID:
        return

    if not message.attachments:
        return

    file = message.attachments[0]
    content = (await file.read()).decode(errors="ignore")

    status = "🟢 Aman"
    if "telegram" in content.lower():
        status = "🟡 Mencurigakan"
    if "webhook" in content.lower() or "http" in content.lower():
        status = "🔴 Bahaya"

    embed = discord.Embed(
        title="🛡 Scan Result",
        description=f"File: `{file.filename}`\nStatus: **{status}**",
        color=0xff0000 if "Bahaya" in status else 0xffff00 if "Mencurigakan" in status else 0x00ff00
    )
    await message.channel.send(embed=embed)

bot.run(TOKEN)
