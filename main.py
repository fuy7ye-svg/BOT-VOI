import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask

# إعداد Flask لـ Render
app = Flask(__name__)

@app.route('/')
def health_check():
    return "OK", 200

# إعدادات البوت
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash Commands Synced!")

bot = MyBot()
rooms_data = {}

# --- ضع الـ IDs الخاصة بك هنا ---
CATEGORY_ID = 1477063895641493526 
CREATOR_CHANNEL_ID = 1477064187715780628 

# (هنا تضع باقي الكود الخاص بالـ Modal والأزرار والـ vckick الذي أرسلته لك سابقاً)
# ... [نفس الكود السابق] ...

@bot.event
async def on_ready():
    print(f'🚀 Bot is online as {bot.user}')

if __name__ == "__main__":
    # تشغيل البوت
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ No Token Found in Environment Variables!")
