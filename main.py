import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# 1. إعداد Flask (الخدعة المجانية)
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Render يطلب بورت 10000 للخدمات المجانية
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# 2. إعدادات البوت
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
CATEGORY_ID = 1477063895641493526  # آيدي الفئة
CREATOR_CHANNEL_ID = 1477064187715780628  # آيدي روم الإنشاء

# --- نافذة تعبئة البيانات (الاسم والعدد) ---
class NameModal(discord.ui.Modal, title="إنشاء رومك الخاص"):
    room_name = discord.ui.TextInput(label="اسم الروم", placeholder="روم السوالف", max_length=15)
    user_limit = discord.ui.TextInput(label="الحد الأقصى (0-99)", placeholder="5", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        limit = int(self.user_limit.value) if self.user_limit.value.isdigit() else 0
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        new_channel = await guild.create_voice_channel(
            name=f"🎙️ | {self.room_name.value}",
            category=category,
            user_limit=limit if 0 <= limit <= 99 else 0
        )

        rooms_data[new_channel.id] = interaction.user.id
        
        if interaction.user.voice:
            await interaction.user.move_to(new_channel)
            await interaction.response.send_message(f"✅ تم إنشاء رومك: {new_channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ تم إنشاء الروم: {new_channel.mention} (ادخل الروم الآن)", ephemeral=True)

# --- واجهة الأزرار ---
class CreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="أنشئ رومك الآن", style=discord.ButtonStyle.success, custom_id="create_voice")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NameModal())

# --- أوامر السلاش ---
@bot.tree.command(name="setup", description="إرسال لوحة التحكم")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(title="🎙️ نظام الرومات المؤقتة", description="اضغط الزر بالأسفل لإنشاء رومك.", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=CreationView())
    await interaction.response.send_message("تم الإرسال!", ephemeral=True)

@bot.tree.command(name="vckick", description="طرد عضو (لا يشمل الأدمن)")
async def vckick(interaction: discord.Interaction, target: discord.Member):
    if not interaction.user.voice or interaction.user.voice.channel.id not in rooms_data:
        return await interaction.response.send_message("❌ لست في رومك الخاص!", ephemeral=True)
    
    if target.guild_permissions.administrator:
        return await interaction.response.send_message("🛡️ لا يمكن طرد الأدمن!", ephemeral=True)

    await target.move_to(None)
    await interaction.response.send_message(f"✅ تم طرد {target.mention}")

# --- تنظيف الرومات ---
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in rooms_data:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del rooms_data[before.channel.id]

# تشغيل السيرفر والبوت
if __name__ == "__main__":
    keep_alive() # تشغيل Flask في ثريد منفصل
    bot.run(os.getenv("DISCORD_TOKEN"))
