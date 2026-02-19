import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import yt_dlp
import re

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
    "📺": "monitor", "⌨️": "teclado", "📨": "cupom", "🗄️": "gabinete",
    "📼": "placa de vídeo", "🪢": "filtro de linha", "📝": "memória",
    "🔌": "fonte", "📱": "smartphone", "🎙️": "microfone", "👓": "acessórios",
    "👩‍👦": "placa mãe", "🆒": "cooler", "⏹️": "processador", "🍀": "Sorteio"
}

# ======== CONFIGURAÇÕES DE MÚSICA (SABR BYPASS & CLOUD FIX) ========
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'ignoreerrors': True, # Permite que o código continue se o YT bloquear
    'source_address': '0.0.0.0',
    'force_ipv4': True,
    'cookiefile': 'cookies.txt' if os.path.exists("cookies.txt") else None,
    'extractor_args': {'youtube': {'player_client': ['tv_embedded', 'android']}},
}

FFMPEG_OPTIONS = {
    'before_options': (
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
        '-allowed_extensions ALL' # CORREÇÃO CRÍTICA PARA SOUNDCLOUD
    ),
    'options': '-vn',
}

musica_filas = {}

def get_guild_queue(guild):
    if guild.id not in musica_filas:
        musica_filas[guild.id] = []
    return musica_filas[guild.id]

# ======== LÓGICA DE EXTRAÇÃO INTELIGENTE ========
async def obter_audio(url_ou_termo):
    url_final = None
    titulo_final = url_ou_termo

    # 1. TENTATIVA YOUTUBE
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            busca = f"ytsearch1:{url_ou_termo}" if not url_ou_termo.startswith("http") else url_ou_termo
            info = await asyncio.to_thread(ydl.extract_info, busca, download=False)
            
            if info and 'entries' in info:
                info = info['entries'][0]
            
            if info and 'url' in info:
                url_final = info['url']
                titulo_final = info.get('title', url_ou_termo)
    except Exception as e:
        print(f"DEBUG: YouTube bloqueou ou falhou: {e}")

    # 2. FALLBACK SOUNDCLOUD (SE O YT FALHAR OU FOR BLOQUEADO)
    if not url_final:
        # LIMPEZA DE BUSCA: Não pesquisa a URL no SoundCloud, pesquisa o ID ou o Nome
        termo_limpo = url_ou_termo
        if "youtube.com" in url_ou_termo or "youtu.be" in url_ou_termo:
            video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_ou_termo)
            termo_limpo = video_id.group(1) if video_id else "musica"
        
        print(f"⚠️ YouTube falhou. Buscando '{termo_limpo}' no SoundCloud...")
        try:
            sc_opts = {'format': 'bestaudio', 'quiet': True}
            with yt_dlp.YoutubeDL(sc_opts) as ydl_sc:
                # scsearch1 garante que pegue um resultado musical real
                info_sc = await asyncio.to_thread(ydl_sc.extract_info, f"scsearch1:{termo_limpo}", download=False)
                if info_sc and 'entries' in info_sc and len(info_sc['entries']) > 0:
                    res = info_sc['entries'][0]
                    url_final = res['url']
                    titulo_final = res.get('title', termo_limpo)
        except Exception as e_sc:
            print(f"Erro SoundCloud: {e_sc}")

    return url_final, titulo_final

async def tocar_proxima_musica(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue: return

    proxima = queue.pop(0)
    termo = proxima["termo"]
    msg_status = await ctx.send(f"🔍 Buscando: `{termo}`...")

    url_final, titulo_final = await obter_audio(termo)

    if not url_final:
        await msg_status.edit(content="❌ Não consegui carregar essa música em nenhuma fonte.")
        return await tocar_proxima_musica(ctx)

    def after_playing(error):
        if error: print(f"Erro no player: {error}")
        asyncio.run_coroutine_threadsafe(tocar_proxima_musica(ctx), bot.loop)

    try:
        source = discord.FFmpegPCMAudio(url_final, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=after_playing)
        await msg_status.edit(content=f"🎶 Tocando agora: **{titulo_final}**")
    except Exception as e:
        print(f"Erro FFmpeg: {e}")
        await msg_status.edit(content="❌ Erro ao iniciar áudio. Tentando próxima...")
        await tocar_proxima_musica(ctx)

# ======== COMANDOS DE MÚSICA ========
@bot.command(aliases=['p'])
async def play(ctx, *, termo):
    if not ctx.author.voice:
        return await ctx.send("❌ Você precisa estar em um canal de voz.")
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    get_guild_queue(ctx.guild).append({"termo": termo})

    if not ctx.voice_client.is_playing():
        await tocar_proxima_musica(ctx)
    else:
        await ctx.send(f"✅ Adicionado à fila: `{termo}`")

@bot.command(aliases=['s'])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Música pulada!")

@bot.command()
async def stop(ctx):
    get_guild_queue(ctx.guild).clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("🛑 Parado e desconectado.")

# ======== SISTEMA DE CARGOS E SETUP ========
@bot.command()
async def setup(ctx):
    if ctx.channel.name == "cargo-de-promoção-aqui":
        async for m in ctx.channel.history(limit=50):
            if m.author == bot.user: await m.delete()
        
        texto = "Reaja para obter os cargos:\n" + "\n".join([f"{e} - {r}" for e, r in emoji_to_role.items()])
        msg = await ctx.send(texto)
        for emoji in emoji_to_role.keys(): await msg.add_reaction(emoji)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user: return
    role_name = emoji_to_role.get(str(reaction.emoji))
    if role_name and reaction.message.channel.id == 1267971255684960266:
        role = discord.utils.get(reaction.message.guild.roles, name=role_name)
        member = await reaction.message.guild.fetch_member(user.id)
        if role: await member.add_roles(role)

@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: return
    role_name = emoji_to_role.get(str(reaction.emoji))
    if role_name and reaction.message.channel.id == 1267971255684960266:
        role = discord.utils.get(reaction.message.guild.roles, name=role_name)
        member = await reaction.message.guild.fetch_member(user.id)
        if role: await member.remove_roles(role)

# ======== MONITOR DE PROMOS ========
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    if message.channel.name == "promos":
        keywords = {
            "@monitor": "monitor", "@teclado": "teclado", "@gabinete": "gabinete",
            "@cupom": "cupom", "@placa de vídeo": "placa de vídeo", "@fonte": "fonte",
            "@smartphone": "smartphone", "@processador": "processador", "sorteio": "Sorteio"
        }
        for kw, rn in keywords.items():
            if kw in message.content.lower():
                role = discord.utils.get(message.guild.roles, name=rn)
                if role: await message.channel.send(f"<@&{role.id}>")

@bot.event
async def on_ready():
    print(f'✅ Bot online como {bot.user}')

bot.run(Meu_token)