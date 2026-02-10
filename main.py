import discord
from discord import app_commands
from discord.ext import commands
import base64, random, string, tempfile, os, time
import yt_dlp
import qrcode
import requests

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

start_time = time.time()

# ======================
# UTIL
# ======================
def rand_var():
    return ''.join(random.choices(string.ascii_letters, k=8))

def obfuscate_code(text, level):
    if level == "low":
        encoded = base64.b64encode(text.encode()).decode()
        return f'import base64\nexec(base64.b64decode("{encoded}").decode())'

    elif level == "medium":
        encoded = base64.b64encode(text.encode()).decode()[::-1]
        v = rand_var()
        return f'import base64\n{v}="{encoded}"\nexec(base64.b64decode({v}[::-1]).decode())'

    elif level == "hard":
        encoded = base64.b64encode(text.encode()).decode()
        parts = [encoded[i:i+10] for i in range(0, len(encoded), 10)]
        var = rand_var()
        joined = " + ".join([f'"{p}"' for p in parts])
        return f'import base64\n{var} = {joined}\nexec(base64.b64decode({var}).decode())'

# ======================
# BUTTON VIEW OBF
# ======================
class ObfView(discord.ui.View):
    def __init__(self, file):
        super().__init__(timeout=60)
        self.file = file

    async def process(self, interaction, level):
        data = await self.file.read()
        text = data.decode("utf-8", errors="ignore")

        result = obfuscate_code(text, level)

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
        temp.write(result.encode())
        temp.close()

        await interaction.response.send_message(
            content=f"✅ **Obfuscation {level.upper()} berhasil! 🔐**",
            file=discord.File(temp.name, filename=f"obf_{level}.py"),
            ephemeral=True
        )

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
# /menu
# ======================
@bot.tree.command(name="menu", description="Menu Bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 BOT MENU",
        description="Bot Tools & Utility Serba Guna ⚙️",
        color=0x00ffcc
    )

    embed.add_field(name="🛡️ SECURITY", value="`/obf` Obfuscate Script", inline=False)
    embed.add_field(name="📥 DOWNLOAD", value="`/youtube` Download Video", inline=False)
    embed.add_field(name="🧰 TOOLS", value=(
        "`/ping`\n"
        "`/uptime`\n"
        "`/calc`\n"
        "`/shorturl`\n"
        "`/qr`\n"
        "`/note`\n"
        "`/userinfo`\n"
        "`/serverinfo`"
    ), inline=False)

    embed.set_footer(text="Bot Ready 24/7 ⚡")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================
# /obf
# ======================
@bot.tree.command(name="obf", description="Obfuscate script dengan button")
@app_commands.describe(file="Upload file python")
async def obf(interaction: discord.Interaction, file: discord.Attachment):
    embed = discord.Embed(
        title="🔐 OBFUSCATION TOOL",
        description="Pilih level:\n🟢 Low\n🟡 Medium\n🔴 Hard",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed, view=ObfView(file), ephemeral=True)

# ======================
# TOOLS
# ======================
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="uptime")
async def uptime(interaction: discord.Interaction):
    seconds = int(time.time() - start_time)
    await interaction.response.send_message(f"⏰ Uptime: {seconds} detik")

@bot.tree.command(name="calc")
async def calc(interaction: discord.Interaction, expr: str):
    try:
        result = eval(expr)
        await interaction.response.send_message(f"🧮 Hasil: {result}")
    except:
        await interaction.response.send_message("❌ Rumus salah")

@bot.tree.command(name="shorturl")
async def shorturl(interaction: discord.Interaction, url: str):
    api = f"https://tinyurl.com/api-create.php?url={url}"
    short = requests.get(api).text
    await interaction.response.send_message(f"🔗 {short}")

@bot.tree.command(name="qr")
async def qr(interaction: discord.Interaction, text: str):
    img = qrcode.make(text)
    img.save("qr.png")
    await interaction.response.send_message(file=discord.File("qr.png"))

@bot.tree.command(name="note")
async def note(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"📝 Catatan:\n{text}")

@bot.tree.command(name="userinfo")
async def userinfo(interaction: discord.Interaction):
    user = interaction.user
    await interaction.response.send_message(f"👤 {user.name}\n🆔 {user.id}")

@bot.tree.command(name="serverinfo")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.send_message(f"🏠 {guild.name}\n👥 {guild.member_count}")

# ======================
# YOUTUBE DOWNLOAD
# ======================
@bot.tree.command(name="youtube", description="Download video YouTube")
async def youtube(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    ydl_opts = {
        'format': 'mp4',
        'outtmpl': 'video.mp4'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    await interaction.followup.send(file=discord.File("video.mp4"))

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot Ready!")

bot.run(TOKEN)
