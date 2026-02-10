import discord
from discord.ext import commands
from discord import app_commands
import os, zipfile, tempfile, datetime, base64, random, string

TOKEN = os.getenv("TOKEN") or "YOUR_BOT_TOKEN"
SCAN_CHANNEL_ID = 1469740150522380299

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# KEYLOGGER KEYWORDS
# =========================
DANGEROUS_KEYWORDS = [
    "webhook", "discord.com/api", "telegram", "http.request",
    "socket.http", "io.popen", "os.execute", "httppost",
    "curl", "bot.send", "sendmessage", "request.post"
]

SUSPICIOUS_KEYWORDS = [
    "base64", "string.reverse", "keylog",
    "encode", "decode", "clipboard"
]

# =========================
# LUA OBFUSCATION
# =========================
def rand_var():
    return ''.join(random.choices(string.ascii_letters, k=8))

def obfuscate_lua(code, level):
    encoded = base64.b64encode(code.encode()).decode()

    if level == "low":
        return f'loadstring(game:HttpGet("data:text/plain;base64,{encoded}"))()'

    elif level == "medium":
        v = rand_var()
        return f'''
local {v} = "{encoded}"
local f = game:HttpGet("data:text/plain;base64,"..{v})
loadstring(f)()
'''

    elif level == "hard":
        parts = [encoded[i:i+15] for i in range(0, len(encoded), 15)]
        var = rand_var()
        joined = " .. ".join([f'"{p}"' for p in parts])
        return f'''
local {var} = {joined}
local f = game:HttpGet("data:text/plain;base64,"..{var})
loadstring(f)()
'''

# =========================
# SCAN TEXT
# =========================
def scan_text(text: str):
    text = text.lower()
    found_danger = [k for k in DANGEROUS_KEYWORDS if k in text]
    found_suspicious = [k for k in SUSPICIOUS_KEYWORDS if k in text]

    if found_danger:
        return "🔴 BAHAYA", 0xe74c3c, found_danger
    elif found_suspicious:
        return "🟡 MENCURIGAKAN", 0xf1c40f, found_suspicious
    else:
        return "🟢 AMAN", 0x2ecc71, []

# =========================
# FILE SCAN
# =========================
async def scan_file(message, attachment):
    filename = attachment.filename.lower()
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, attachment.filename)
    await attachment.save(file_path)

    results = []

    if filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                if f.endswith(".lua") or f.endswith(".luac"):
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r", errors="ignore") as file:
                            text = file.read()
                        status, color, found = scan_text(text)
                        results.append((f, status, found))
                    except:
                        pass

    elif filename.endswith(".lua") or filename.endswith(".luac"):
        with open(file_path, "r", errors="ignore") as f:
            text = f.read()
        status, color, found = scan_text(text)
        results.append((attachment.filename, status, found))

    else:
        return

    # Global status
    if any("🔴" in r[1] for r in results):
        final_status = "🔴 BAHAYA"
        final_color = 0xe74c3c
        desc = "Terdeteksi keylogger / webhook berbahaya."
    elif any("🟡" in r[1] for r in results):
        final_status = "🟡 MENCURIGAKAN"
        final_color = 0xf1c40f
        desc = "Ditemukan pola mencurigakan."
    else:
        final_status = "🟢 AMAN"
        final_color = 0x2ecc71
        desc = "Tidak ditemukan indikasi keylogger."

    embed = discord.Embed(
        title="🛡️ Tatang SA‑MP Scanner Result",
        description=desc,
        color=final_color,
        timestamp=datetime.datetime.utcnow()
    )

    embed.add_field(name="📦 File", value=attachment.filename, inline=False)
    embed.add_field(name="👤 User", value=message.author.mention, inline=True)
    embed.add_field(name="📊 Status", value=final_status, inline=True)

    detail_text = ""
    for fname, status, found in results:
        detail_text += f"{fname} → {status}\n"
        if found:
            detail_text += "  └ " + ", ".join(found) + "\n"

    embed.add_field(
        name="🧪 Detail Scan",
        value=f"```\n{detail_text}\n```",
        inline=False
    )

    embed.set_footer(text="Tatang SA‑MP Ultimate Scanner")

    await message.channel.send(embed=embed)

# =========================
# OBF BUTTON VIEW
# =========================
class ObfView(discord.ui.View):
    def __init__(self, file, interaction):
        super().__init__(timeout=60)
        self.file = file
        self.interaction = interaction

    async def process(self, interaction, level):
        data = await self.file.read()
        text = data.decode("utf-8", errors="ignore")

        result = obfuscate_lua(text, level)

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".lua")
        temp.write(result.encode())
        temp.close()

        await interaction.response.send_message(
            content=f"✅ Obfuscation {level.upper()} selesai",
            file=discord.File(temp.name, filename=f"obf_{level}.lua"),
            ephemeral=True
        )

        # AUTO DELETE FILE USER (HANYA DI /obf)
        try:
            await self.interaction.message.delete()
        except:
            pass

        os.remove(temp.name)

    @discord.ui.button(label="🟢 LOW", style=discord.ButtonStyle.success)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "low")

    @discord.ui.button(label="🟡 MEDIUM", style=discord.ButtonStyle.primary)
    async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "medium")

    @discord.ui.button(label="🔴 HARD", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "hard")

# =========================
# /obf COMMAND
# =========================
@bot.tree.command(name="obf", description="Obfuscate Lua script")
async def obf(interaction: discord.Interaction, file: discord.Attachment):
    embed = discord.Embed(
        title="🛡️ Tatang SA‑MP Lua Obfuscator",
        description="Pilih level obfuscation:",
        color=0x3498db
    )

    await interaction.response.send_message(
        embed=embed,
        view=ObfView(file, interaction),
        ephemeral=True
    )

# =========================
# AUTO SCAN EVENT
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == SCAN_CHANNEL_ID and message.attachments:
        await scan_file(message, message.attachments[0])
        return

    await bot.process_commands(message)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Tatang SA‑MP Ultimate Bot Ready!")

bot.run(TOKEN)
