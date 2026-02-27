import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio # ضروري لعملية التأخير قبل الحذف
from flask import Flask
from threading import Thread

# --- إعداد Flask لتشغيل البوت على Render مجاناً ---
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
        await self.tree.sync()
        print(f"✅ تم تحديث أوامر السلاش بنجاح!")

bot = MyBot()
rooms_data = {} # تخزين بيانات الرومات: {آيدي_الروم: آيدي_الليدر}

# --- إعدادات الـ IDs (تأكد من وضع الأرقام الصحيحة هنا) ---
CATEGORY_ID = 1477063895641493526  # آيدي الفئة التي ستظهر فيها الرومات
CREATOR_CHANNEL_ID = 1477064187715780628  # آيدي روم "أنشئ رومك"

# --- نافذة إعداد الروم (Modal) ---
class NameModal(discord.ui.Modal, title="إعداد الروم المؤقت"):
    room_name = discord.ui.TextInput(label="اسم الروم", placeholder="مثلاً: روم الوناسة", max_length=15)
    user_limit = discord.ui.TextInput(label="الحد الأقصى (0 = مفتوح)", placeholder="5", default="0", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        # التحقق من المدخلات
        if not self.user_limit.value.isdigit():
            return await interaction.response.send_message("❌ خطأ: يجب إدخال رقم في خانة العدد!", ephemeral=True)
        
        limit = int(self.user_limit.value)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        # إنشاء الروم الصوتي
        new_channel = await guild.create_voice_channel(
            name=f"🎙️ | {self.room_name.value}",
            category=category,
            user_limit=limit if 0 <= limit <= 99 else 0
        )

        rooms_data[new_channel.id] = interaction.user.id
        
        # نقل العضو للروم الجديد وحذف رسالة التأكيد بعد 5 ثوانٍ
        if interaction.user.voice:
            await interaction.user.move_to(new_channel)
            await interaction.response.send_message(f"✅ تم إنشاء رومك ونقلك إليه: {new_channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ تم إنشاء الروم: {new_channel.mention} (ادخل الروم لتفعيله)", ephemeral=True)

# --- واجهة الأزرار ---
class CreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="أنشئ رومك الآن", style=discord.ButtonStyle.success, custom_id="create_vc_btn", emoji="➕")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NameModal())

# --- الأوامر (Slash Commands) ---

@bot.tree.command(name="setup", description="إرسال لوحة تحكم الرومات المؤقتة")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎙️ نظام الرومات الصوتية المؤقتة",
        description=(
            "اضغط على الزر بالأسفل لإنشاء مساحتك الخاصة!\n\n"
            "**🛠️ أوامر التحكم لليدر:**\n"
            "• `/vckick` : لطرد شخص من رومك.\n"
            "• `/set_owner` : لنقل ملكية الروم لشخص آخر.\n\n"
            "⚠️ *يتم حذف الروم تلقائياً عند خروج الجميع.*"
        ),
        color=discord.Color.from_rgb(46, 204, 113)
    )
    embed.set_footer(text="نظام الرومات الصوتية")
    
    await interaction.channel.send(embed=embed, view=CreationView())
    await interaction.response.send_message("✅ تم إرسال القائمة بنجاح.", ephemeral=True)

@bot.tree.command(name="vckick", description="طرد عضو من رومك الخاص")
async def vckick(interaction: discord.Interaction, target: discord.Member):
    # التأكد من وجود العضو في روم يملكه
    if not interaction.user.voice or interaction.user.voice.channel.id not in rooms_data:
        return await interaction.response.send_message("❌ يجب أن تكون داخل رومك الخاص لاستخدام هذا الأمر!", ephemeral=True)
    
    channel_id = interaction.user.voice.channel.id
    if rooms_data[channel_id] != interaction.user.id:
        return await interaction.response.send_message("⚠️ أنت لست صاحب هذا الروم!", ephemeral=True)

    # حماية الإداريين
    if target.guild_permissions.administrator:
        return await interaction.response.send_message("🛡️ لا يمكن طرد الإداريين من الروم.", ephemeral=True)

    if target.voice and target.voice.channel.id == channel_id:
        await target.move_to(None)
        # إرسال رسالة وحذفها تلقائياً بعد 5 ثوانٍ
        await interaction.response.send_message(f"👤 تم طرد {target.mention} من الروم.")
        await asyncio.sleep(5)
        await interaction.delete_original_response()
    else:
        await interaction.response.send_message("العضو غير موجود في رومك حالياً.", ephemeral=True)

@bot.tree.command(name="set_owner", description="نقل ملكية الروم لعضو آخر")
async def set_owner(interaction: discord.Interaction, new_owner: discord.Member):
    if not interaction.user.voice or interaction.user.voice.channel.id not in rooms_data:
        return await interaction.response.send_message("❌ يجب أن تكون داخل رومك الخاص لنقل الملكية!", ephemeral=True)
    
    channel_id = interaction.user.voice.channel.id
    if rooms_data[channel_id] != interaction.user.id:
        return await interaction.response.send_message("⚠️ أنت لست صاحب هذا الروم!", ephemeral=True)

    if new_owner.bot:
        return await interaction.response.send_message("❌ لا يمكنك نقل الملكية لبوت.", ephemeral=True)

    rooms_data[channel_id] = new_owner.id
    await interaction.response.send_message(f"👑 تم نقل ملكية الروم إلى {new_owner.mention}")
    await asyncio.sleep(5)
    await interaction.delete_original_response()

# --- حذف الروم عند خروج الجميع ---
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in rooms_data:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                if before.channel.id in rooms_data:
                    del rooms_data[before.channel.id]
            except: pass

# --- التشغيل ---
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)
