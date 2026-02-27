import discord
from discord.ext import commands
import os

# إعدادات الصلاحيات
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# تخزين بيانات الرومات: {channel_id: owner_id}
rooms_data = {}

# --- إعدادات السيرفر (استبدلها بالأرقام الخاصة بك) ---
CATEGORY_ID = 1477063895641493526  # آيدي الفئة
CREATOR_CHANNEL_ID = 1477064187715780628  # آيدي روم "اضغط للإنشاء"

@bot.event
async def on_ready():
    print(f'✅ البوت متصل كـ: {bot.user}')

@bot.event
async def on_voice_state_update(member, before, after):
    # إذا دخل العضو روم الإنشاء
    if after.channel and after.channel.id == CREATOR_CHANNEL_ID:
        guild = member.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        # إرسال رسالة خاصة للعضو تسأله عن الإعدادات (أو استخدام قيم افتراضية)
        # لتسهيل الأمر برمجياً، سنقوم بإنشاء الروم أولاً ثم نطلب منه التعديل
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(move_members=True, manage_channels=True)
        }

        new_channel = await guild.create_voice_channel(
            name=f"🎙️ | {member.display_name}",
            category=category,
            user_limit=5, # العدد الافتراضي
            overwrites=overwrites
        )

        rooms_data[new_channel.id] = member.id
        await member.move_to(new_channel)
        
        await new_channel.send(f"مرحباً {member.mention}! أنت ليدر الروم الآن.\n"
                               f"تستطيع تغيير الاسم بـ: `!name [الاسم]`\n"
                               f"وتغيير العدد بـ: `!limit [العدد]`\n"
                               f"لطرد شخص (غير الإداريين): `!vckick @user`")

# --- أمر تغيير اسم الروم ---
@bot.command()
async def name(ctx, *, new_name: str):
    if ctx.author.voice and ctx.author.voice.channel.id in rooms_data:
        if rooms_data[ctx.author.voice.channel.id] == ctx.author.id:
            await ctx.author.voice.channel.edit(name=f"🎙️ | {new_name}")
            await ctx.send(f"✅ تم تغيير اسم الروم إلى: **{new_name}**")

# --- أمر تغيير عدد الأشخاص ---
@bot.command()
async def limit(ctx, num: int):
    if ctx.author.voice and ctx.author.voice.channel.id in rooms_data:
        if rooms_data[ctx.author.voice.channel.id] == ctx.author.id:
            if 0 <= num <= 99:
                await ctx.author.voice.channel.edit(user_limit=num)
                await ctx.send(f"✅ تم تغيير الحد الأقصى إلى: **{num}**")

# --- أمر الطرد (مع حماية الإداريين) ---
@bot.command()
async def vckick(ctx, target: discord.Member):
    if not ctx.author.voice or ctx.author.voice.channel.id not in rooms_data:
        return await ctx.send("❌ لست ليدر لروم مؤقت.")

    if rooms_data[ctx.author.voice.channel.id] != ctx.author.id:
        return await ctx.send("⚠️ لست صاحب هذا الروم.")

    # حماية الأدمن ورتبة معينة (مثلاً أي شخص ليس لديه رتبة 'Member')
    if target.guild_permissions.administrator:
        return await ctx.send("🛡️ لا يمكنك طرد إداري!")

    if target.voice and target.voice.channel.id == ctx.author.voice.channel.id:
        await target.move_to(None)
        await ctx.send(f"✅ تم طرد {target.mention}.")

# حذف الروم عند خروج الجميع
@bot.event
async def on_voice_state_update_cleanup(member, before, after):
    if before.channel and before.channel.id in rooms_data:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del rooms_data[before.channel.id]

# تشغيل البوت
bot.run(os.getenv("DISCORD_TOKEN"))
