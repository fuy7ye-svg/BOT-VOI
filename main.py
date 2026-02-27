import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- أولاً: جزء الـ Flask لتخطي مشكلة Render ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    # Render يطلب تشغيل سيرفر على بورت 10000 في الـ Web Service
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ثانياً: إعدادات البوت ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ تم مزامنة أوامر السلاش!")

bot = MyBot()
rooms_data = {} # {channel_id: owner_id}

# --- إعدادات الـ IDs (عدلها هنا) ---
CATEGORY_ID = 1477063895641493526  # آيدي الفئة
CREATOR_CHANNEL_ID = 1477064187715780628  # آيدي روم الإنشاء

# --- نافذة تغيير الاسم والعدد ---
class NameModal(discord.ui.Modal, title="إعدادات الروم الجديد"):
    room_name = discord.ui.TextInput(label="اسم الروم", placeholder="اكتب اسم الروم هنا...", max_length=15)
    user_limit = discord.ui.TextInput(label="عدد الأشخاص (0 = بدون حد)", placeholder="5", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.user_limit.value.isdigit():
            return await interaction.response.send_message("❌ الرجاء إدخال رقم صحيح!", ephemeral=True)
        
        limit = int(self.user_limit.value)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        # إنشاء الروم
        new_channel = await guild.create_voice_channel(
            name=f"🎙️ | {self.room_name.value}",
            category=category,
            user_limit=limit if 0 <= limit <= 99 else 0
        )

        rooms_data[new_channel.id] = interaction.user.id
        
        # نقل العضو إذا كان متصلاً بالصوت
        if interaction.user.voice:
            await interaction.user.move_to(new_channel)
            await interaction.response.send_message(f"✅ تم إنشاء رومك ونقلك: {new_channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ تم إنشاء الروم: {new_channel.mention} (ادخل الروم لتفعيله)", ephemeral=True)

# --- واجهة الأزرار في القناة ---
class CreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="أنشئ رومك الخاص", style=discord.ButtonStyle.success, custom_id="create_room")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NameModal())

# --- الأوامر ---
@bot.tree.command(name="setup", description="إرسال لوحة تحكم إنشاء الرومات")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎙️ نظام الرومات الصوتية",
        description="اضغط على الزر بالأسفل لإنشاء رومك الخاص بتحديد الاسم والعدد.\n\n"
                    "🛡️ **ملاحظة:** لا يمكن لصاحب الروم طرد الإداريين.",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=CreationView())
    await interaction.response.send_message("✅ تم إرسال القائمة بنجاح.", ephemeral=True)

@bot.tree.command(name="vckick", description="طرد عضو من رومك (للأعضاء فقط)")
async def vckick(interaction: discord.Interaction, target: discord.Member):
    if not interaction.user.voice or interaction.user.voice.channel.id not in rooms_data:
        return await interaction.response.send_message("❌ لست في روم مؤقت خاص بك!", ephemeral=True)

    if rooms_data[interaction.user.voice.channel.id] != interaction.user.id:
        return await interaction.response.send_message("⚠️ لست ليدر هذا الروم!", ephemeral=True)

    # حماية الأدمن
    if target.guild_permissions.administrator:
        return await interaction.response.send_message("🛡️ لا يمكنك طرد هذا الشخص لأنه أدمن!", ephemeral=True)

    if target.voice and target.voice.channel.id == interaction.user.voice.channel.id:
        await target.move_to(None)
        await interaction.response.send_message(f"✅ تم طرد {target.mention}.")
    else:
        await interaction.response.send_message("العضو ليس في رومك.", ephemeral=True)

# تنظيف الرومات
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in rooms_data:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                del rooms_data[before.channel.id]
            except: pass

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# تشغيل الـ Flask والبوت
keep_alive()
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
