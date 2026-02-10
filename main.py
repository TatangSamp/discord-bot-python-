import discord
from discord import app_commands
from discord.ext import commands
import base64, random, string, tempfile, os, datetime

TOKEN = os.getenv("TOKEN") or "YOUR_BOT_TOKEN"

SCAN_CHANNEL_ID = 1469740150522380299

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# KEYWORDS SCANNER
# ======================
DANGEROUS_KEYWORDS = [
    "webhook", "discord.com/api", "telegram", "http.request",
    "socket.http", "io.popen", "os.execute", "loadstring",
    "curl", "HttpPost"
]

SUSPICIOUS_KEYWORDS = [
    "base64", "string.reverse", "keylog", "clipboard",
    "encode", "decode"
]

# ======================
# UTIL
# ======================
def rand_var():
    return ''.join(random.choices(string.ascii_letters, k=8))

def obfuscate_lua(code, level):
    if level == "low":
        encoded = base64.b64encode(code.encode()).decode()
        return f'local d=("{encoded}")\nloadstring(require("mime").unb64(d))()'

    elif level == "medium":
        encoded = base64.b64encode(code.encode()).decode()[::-1]
        v = rand_var()
        return f'local {v}="{encoded}"\nloadstring(require("mime").unb64(string.reverse({v})))()'

    elif level == "hard":
        encoded = base64.b64encode(code.encode()).decode()
        parts = [encoded[i:i+15] for i in range(0, len(encoded), 15)]
        joined = " .. ".join([f'"{p}"' for p in parts])
        v = rand_var()
        return f'local {v}={joined}\nloadstring(require("mime").unb64({v}))()'

# ======================
# OBF BUTTON VIEW
# ======================
class ObfView(discord.ui.View):
    def __init__(self, file):
        super().__init__(timeout=60)
        self.file = file

    async def process(self, interaction, level):
        data = await self.file.read()
        text = data.decode("utf-8", errors="ignore")

        result = obfuscate_lua(text, level)

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".lua")
        temp.write(result.encode())
        temp.close()

        await interaction.response.send_message(
            content=f"✅ **OBFUSCATION {level.upper()} BERHASIL 🔐**",
            file=discord.File(temp.name, filename=f"obf_{level}.lua"),
            ephemeral=True
        )

        os.remove(temp.name)  # auto delete hasil temp

    @discord.ui.button(label="🟢 LOW", style=discord.ButtonStyle.success)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "low")

    @discord.ui.button(label="🟡 MEDIUM", style=discord.ButtonStyle.primary)
    async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "medium")

    @discord.ui.button(label="🔴 HARD", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "hard")

# ======================
# /obf COMMAND
# ======================
@bot.tree.command(name="obf", description="Obfuscate Lua Script")
@app_commands.describe(file="Upload file lua/luac")
async def obf(interaction: discord.Interaction, file: discord.Attachment):
    embed = discord.Embed(
        title="🛡️ Tatang SA-MP Obfuscator",
        description="Pilih tingkat obfuscation:\n\n🟢 LOW\n🟡 MEDIUM\n🔴 HARD",
        color=0x00ffcc
    )
    await interaction.response.send_message(embed=embed, view=ObfView(file), ephemeral=True)

# ======================
# SCANNER FUNCTION
# ======================
async def scan_lua_file(message, attachment):
    data = await attachment.read()
    text = data.decode("utf-8", errors="ignore").lower()

    found_danger = [k for k in DANGEROUS_KEYWORDS if k in text]
    found_suspicious = [k for k in SUSPICIOUS_KEYWORDS if k in text]

    if found_danger:
        status = "🔴 BAHAYA"
        color = 0xe74c3c
        desc = "File terindikasi **KEYLOGGER / WEBHOOK SCRIPT**!"
        found = found_danger
    elif found_suspicious:
        status = "🟡 MENCURIGAKAN"
        color = 0xf1c40f
        desc = "Ditemukan pola mencurigakan. Periksa manual."
        found = found_suspicious
    else:
        status = "🟢 AMAN"
        color = 0x2ecc71
        desc = "Tidak ditemukan indikasi berbahaya."
        found = []

    embed = discord.Embed(
        title="🛡️ Tatang SA-MP Scanner Result",
        description=desc,
        color=color,
        timestamp=datetime.datetime.utcnow()
    )

    embed.add_field(name="📂 File", value=attachment.filename, inline=False)
    embed.add_field(name="👤 User", value=message.author.mention, inline=True)
    embed.add_field(name="📊 Status", value=status, inline=True)

    if found:
        embed.add_field(
            name="🧪 Indikasi",
            value="```\n" + "\n".join(found) + "\n```",
            inline=False
        )
    else:
        embed.add_field(name="🧪 Indikasi", value="Tidak ada", inline=False)

    embed.set_footer(text="Tatang SA-MP Security Scanner")

    await message.channel.send(embed=embed)

    # auto delete file user
    try:
        await message.delete()
    except:
        pass

# ======================
# AUTO SCAN ON MESSAGE
# ======================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == SCAN_CHANNEL_ID and message.attachments:
        attachment = message.attachments[0]
        if attachment.filename.endswith(".lua") or attachment.filename.endswith(".luac"):
            await scan_lua_file(message, attachment)

    await bot.process_commands(message)

# ======================
# /menu
# ======================
@bot.tree.command(name="menu")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Tatang SA-MP Ultimate Bot",
        description="**Security • Obfuscator • Scanner**",
        color=0x3498db
    )

    embed.add_field(
        name="🛡️ SECURITY",
        value="`/obf` → Lua Obfuscation\nAuto Scan di channel scanner",
        inline=False
    )

    embed.add_field(
        name="📂 SCANNER CHANNEL",
        value=f"<#{SCAN_CHANNEL_ID}>",
        inline=False
    )

    embed.set_footer(text="Tatang SA-MP Ultimate System")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Tatang SA-MP Ultimate Bot Ready!")

bot.run(TOKEN)
