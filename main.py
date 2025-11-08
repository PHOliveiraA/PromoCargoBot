import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import yt_dlp

# ======== CONFIGURAÇÕES INICIAIS ========
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!!', intents=intents)
load_dotenv()
Meu_token = os.getenv("DISCORD_TOKEN")

# ======== DICIONÁRIO DE CARGOS ========
emoji_to_role = {
    "📺": "monitor",
    "⌨️": "teclado",
    "📨": "cupom",
    "🗄️": "gabinete",
    "📼": "placa de vídeo",
    "🪢": "filtro de linha",
    "📝": "memória",
    "🔌": "fonte",
    "📱": "smartphone",
    "🎙️": "microfone",
    "👓": "acessórios",
    "👩‍👦": "placa mãe",
    "🆒": "cooler",
    "⏹️": "processador",
    "🍀": "Sorteio"
}

# ======== FUNÇÕES AUXILIARES ========
async def clear_old_setup_messages(channel):
    async for message in channel.history(limit=100):
        try:
            if message.author == bot.user and "Reaja com os emojis abaixo" in message.content:
                await message.delete()
            elif message.content.startswith("!!setup"):
                await message.delete()
        except discord.HTTPException as e:
            print(f"Erro ao deletar mensagem: {e}")

async def condicoes(reaction):
    role_name = emoji_to_role.get(reaction.emoji)
    if role_name:
        return discord.utils.get(reaction.message.guild.roles, name=role_name)
    return None

# ======== COMANDO DE SETUP ========
@bot.command()
async def setup(ctx):
    channels = ["cargo-de-promoção-aqui"]
    if str(ctx.channel.name) in channels:
        await clear_old_setup_messages(ctx.channel)

        message_text = "Reaja com os emojis abaixo para obter cargos:\n"
        for emoji, role in emoji_to_role.items():
            message_text += f"{emoji} - {role}\n"

        message = await ctx.send(message_text)
        for emoji in emoji_to_role.keys():
            await message.add_reaction(emoji)

# ======== EVENTOS DE REAÇÃO ========
@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return
    if reaction.message.channel.id == 1267971255684960266:
        role = await condicoes(reaction)
        if role:
            member = await reaction.message.guild.fetch_member(user.id)
            await member.add_roles(role)
            print(f'Cargo {role.name} adicionado a {user.name}')

@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user:
        return
    if reaction.message.channel.id == 1267971255684960266:
        role = await condicoes(reaction)
        if role:
            member = await reaction.message.guild.fetch_member(user.id)
            await member.remove_roles(role)
            print(f'Cargo {role.name} removido de {user.name}')

# ======== SISTEMA DE MÚSICA ========
musica_filas = {}

def get_guild_queue(guild):
    if guild.id not in musica_filas:
        musica_filas[guild.id] = []
    return musica_filas[guild.id]

# ======== FUNÇÃO AUXILIAR PARA OBTER ÁUDIO ========
async def obter_audio(url):
    # converte YouTube para Piped
    if "youtube.com" in url or "youtu.be" in url:
        video_id = url.split("v=")[-1] if "v=" in url else url.split("/")[-1]
        url = f"https://piped.video/watch?v={video_id}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'geo_bypass': True,
        'source_address': '0.0.0.0'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get('url'), info.get('title', 'Música desconhecida')

# ======== FUNÇÃO DE TOCAR MÚSICA ========
async def tocar_proxima_musica(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue:
        await ctx.send("🎵 Fila de músicas vazia.")
        return

    musica_atual = queue.pop(0)
    url = musica_atual["url"]
    titulo = musica_atual["title"]

    try:
        audio_url, titulo_real = await obter_audio(url)
    except Exception as e:
        await ctx.send(f"❌ Erro ao obter áudio: {e}")
        return

    if not audio_url:
        await ctx.send("❌ Não foi possível obter o áudio da música.")
        return

    if not ctx.voice_client or not ctx.voice_client.is_connected():
        try:
            await ctx.author.voice.channel.connect()
        except Exception:
            return

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        ctx.voice_client.stop()

    try:
        # Streaming contínuo com reconexão
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                tocar_proxima_musica(ctx), bot.loop
            )
        )
        await ctx.send(f"🎶 Tocando agora: **{titulo_real}**")
    except Exception as e:
        await ctx.send(f"❌ Erro ao tocar música: {e}")

# ======== COMANDOS DE MÚSICA ========
@bot.command()
async def play(ctx, *, url):
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await ctx.send("❌ Você precisa estar em um canal de voz para tocar música.")
        return

    if not ctx.voice_client:
        await voice_channel.connect()

    try:
        audio_url, titulo = await obter_audio(url)
    except Exception as e:
        await ctx.send(f"❌ Erro ao processar URL: {e}")
        return

    queue = get_guild_queue(ctx.guild)
    queue.append({"url": url, "title": titulo})

    await ctx.send(f"✅ **{titulo}** adicionada à fila!")
    if not ctx.voice_client.is_playing():
        await tocar_proxima_musica(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Pulando música atual...")
    else:
        await ctx.send("❌ Nenhuma música está tocando.")

@bot.command()
async def stop(ctx):
    queue = get_guild_queue(ctx.guild)
    queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("🛑 Música parada e bot desconectado.")

@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música retomada.")

@bot.command()
async def queue(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue:
        await ctx.send("🎵 A fila está vazia.")
    else:
        msg = "\n".join([f"{i+1}. {m['title']}" for i, m in enumerate(queue)])
        await ctx.send(f"📜 **Fila atual:**\n{msg}")

# ======== EVENTO DE MENSAGENS ========
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

    if str(message.channel.name) == "promos":
        keyword_responses = {
            "@monitor": "monitor",
            "@teclado": "teclado",
            "@gabinete": "gabinete",
            "@cupom": "cupom",
            "@placa de vídeo": "placa de vídeo",
            "@filtro de linha": "filtro de linha",
            "@memória": "memória",
            "@fonte": "fonte",
            "@smartphone": "smartphone",
            "@microfone": "microfone",
            "@acessórios": "acessórios",
            "@placa mãe": "placa mãe",
            "@air / water / fan cooler": "cooler",
            "@processador": "processador",
            "sorteio": "Sorteio"
        }

        for keyword, role_name in keyword_responses.items():
            if keyword in message.content.lower():
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role:
                    await message.channel.send(f"<@&{role.id}>")

# ======== EXECUTAR BOT ========
try:
    bot.run(Meu_token)
except discord.errors.DiscordServerError as e:
    print(f"Erro de servidor do Discord: {e}")
