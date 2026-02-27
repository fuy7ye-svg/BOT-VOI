import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread

# --- نظام الحفاظ على العمل (Render) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=10000)
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- إعدادات البوت ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # مزامنة الأوامر مرة واحدة فقط عند التشغيل
        await self.tree.sync()

bot = MyBot()
rooms_data = {}

# --- ضع الـ IDs الخاصة بك هنا ---
CATEGORY_ID = 1477063895641493526  # آيدي الفئة
CREATOR_CHANNEL_ID = 1477064187715780628  # آيدي روم الإنشاء

# --- نافذة إعداد الروم ---
class NameModal(discord.ui.Modal, title="إعداد الروم المؤقت"):
    room_name = discord.ui.TextInput(label="اسم الروم", placeholder="مثلاً: سوالف", max_length=15)
    user_limit = discord.ui.TextInput(label="العدد (0 = مفتوح)", placeholder="5", default="0", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.user_limit.value.isdigit():
            return await interaction.response.send_message("❌ الرجاء إدخال رقم صحيح!", ephemeral=True)
        
        limit = int(self.user_limit.value)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        # 1. إنشاء الروم
        new_channel = await guild.create_voice_channel(
            name=f"🎙️ | {self.room_name.value}",
            category=category,
            user_limit=limit if 0 <= limit <= 99 else 0
        )

        rooms_data[new_channel.id] = interaction.user.id
        
        # 2. النقل الفوري للعضو
        if interaction.user.voice:
            try:
                await interaction.user.move_to(new_channel)
                await interaction.response.send_message(f"✅ تم إنشاء رومك ونقلك إليه فوراً: {new_channel.mention}", ephemeral=True)
            except:
                await interaction.response.send_message(f"✅ تم إنشاء الروم: {new_channel.mention} (تعذر نقلك تلقائياً، ادخل يدوياً)", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ تم إنشاء الروم: {new_channel.mention}\n⚠️ يجب أن تكون في روم صوتي ليتم نقلك تلقائياً.", ephemeral=True)

# --- واجهة الزر (قائمة واحدة فقط) ---
class CreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # الزر يبقى شغال دائماً

    @discord.ui.button(label="أنشئ رومك الآن", style=discord.ButtonStyle.success, custom_id="unique_create_vc", emoji="➕")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NameModal())

# --- الأوامر ---
@bot.tree.command(name="setup", description="إرسال قائمة واحدة فقط للتحكم بالرومات")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    # مسح الرد التلقائي لإرسال رسالة الإمبد فقط
    embed = discord.Embed(
        title="🎙️ نظام الرومات الصوتية المؤقتة",
        description=(
            "اضغط على الزر بالأسفل لإنشاء مساحتك الخاصة!\n\n"
            "**🛠️ أوامر التحكم:**\n"
            "• `/vckick` : لطرد شخص.\n"
            "• `/set_owner` : لنقل الملكية.\n\n"
            "⚠️ *يتم حذف الروم تلقائياً عند خروج الجميع.*"
        ),
        color=discord.Color.brand_green()
    )
    
    await interaction.channel.send(embed=embed, view=CreationView())
    await interaction.response.send_message("✅ تم إرسال القائمة. (احذف الرسائل القديمة يدوياً لمرة واحدة)", ephemeral=True)

@bot.tree.command(name="vckick", description="طرد عضو من رومك")
async def vckick(interaction: discord.Interaction, target: discord.Member):
    if not interaction.user.voice or interaction.user.voice.channel.id not in rooms_data:
        return await interaction.response.send_message("❌ لست في رومك الخاص!", ephemeral=True)
    
    if rooms_data[interaction.user.voice.channel.id] != interaction.user.id:
        return await interaction.response.send_message("⚠️ لست صاحب الروم!", ephemeral=True)

    if target.guild_permissions.administrator:
        return await interaction.response.send_message("🛡️ لا يمكن طرد الأدمن.", ephemeral=True)

    await target.move_to(None)
    await interaction.response.send_message(f"👤 تم طرد {target.mention}")
    await asyncio.sleep(5)
    await interaction.delete_original_response()

# --- تنظيف الرومات ---
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in rooms_data:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                del rooms_data[before.channel.id]
            except: pass

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
