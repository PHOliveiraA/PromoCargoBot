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

# ======== CONFIGURAÇÕES DE MÚSICA (MODO VPS BLINDADO) ========

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'source_address': '0.0.0.0',
    'force_ipv4': True,
    'cookiefile': 'cookies.txt' if os.path.exists("cookies.txt") else None,
    # Alternando para o cliente iOS, que costuma ser mais "gentil" com IPs de VPS
    'extractor_args': {'youtube': {'player_client': ['ios', 'tv']}},
}

# CONFIGURAÇÃO DE PROTOCOLO TOTAL (A chave para o FFmpeg 7.1.3)
FFMPEG_OPTIONS = {
    'before_options': (
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
        '-protocol_whitelist crypto,data,file,http,https,tcp,tls,hls,applehttp ' # Whitelist completa
        '-allowed_extensions ALL' # Permite os segmentos .opus do SoundCloud
    ),
    'options': '-vn',
}

musica_filas = {}

def get_guild_queue(guild_id):
    if guild_id not in musica_filas:
        musica_filas[guild_id] = []
    return musica_filas[guild_id]

# ======== LÓGICA DE BUSCA COM TRATAMENTO DE ID ========

async def obter_audio(url_ou_termo):
    url_final = None
    titulo_final = url_ou_termo

    # 1. TENTATIVA YOUTUBE
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            alvo = url_ou_termo if url_ou_termo.startswith("http") else f"ytsearch1:{url_ou_termo}"
            info = await asyncio.to_thread(ydl.extract_info, alvo, download=False)
            
            if info and 'entries' in info:
                info = info['entries'][0]
            
            if info and 'url' in info:
                url_final = info['url']
                titulo_final = info.get('title', url_ou_termo)
                print(f"✅ Sucesso YouTube: {titulo_final}")
    except Exception as e:
        print(f"❌ YouTube bloqueou/erro: {e}")

    # 2. FALLBACK SOUNDCLOUD (PARA QUANDO O YT DÁ 'FORMAT NOT AVAILABLE')
    if not url_final:
        # Se o YouTube bloqueou, pegamos o ID do vídeo para buscar EXATAMENTE ele no SoundCloud
        termo_sc = titulo_final
        if "youtube.com" in termo_sc or "youtu.be" in termo_sc:
            vid_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", termo_sc)
            termo_sc = vid_id.group(1) if vid_id else "musica"

        print(f"⚠️ Usando fallback: Buscando '{termo_sc}' no SoundCloud...")
        try:
            with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl_sc:
                info_sc = await asyncio.to_thread(ydl_sc.extract_info, f"scsearch1:{termo_sc}", download=False)
                if info_sc and 'entries' in info_sc:
                    res = info_sc['entries'][0]
                    url_final = res['url']
                    titulo_final = res.get('title', termo_sc)
                    print(f"✅ Sucesso SoundCloud: {titulo_final}")
        except Exception as e_sc:
            print(f"❌ Erro SoundCloud: {e_sc}")

    return url_final, titulo_final

# ======== PLAYER PRINCIPAL ========

async def tocar_proxima_musica(ctx):
    queue = get_guild_queue(ctx.guild.id)
    if not queue: return

    musica_atual = queue.pop(0)
    termo = musica_atual["termo"]
    msg_status = await ctx.send(f"🔍 Processando: `{termo}`...")

    url_final, titulo_final = await obter_audio(termo)

    if not url_final:
        await msg_status.edit(content="❌ Erro: Não foi possível obter o áudio de nenhuma fonte.")
        return await tocar_proxima_musica(ctx)

    def after_playing(error):
        if error: print(f"Erro no player: {error}")
        asyncio.run_coroutine_threadsafe(tocar_proxima_musica(ctx), bot.loop)

    try:
        # Criando o player com as flags injetadas diretamente
        source = discord.FFmpegPCMAudio(
            url_final,
            before_options=FFMPEG_OPTIONS['before_options'],
            options=FFMPEG_OPTIONS['options']
        )
        ctx.voice_client.play(source, after=after_playing)
        await msg_status.edit(content=f"🎶 Tocando agora: **{titulo_final}**")
    except Exception as e:
        print(f"Erro FFmpeg 7.1: {e}")
        await msg_status.edit(content="❌ Erro ao iniciar áudio. Pulando...")
        await tocar_proxima_musica(ctx)

# ======== COMANDOS DO BOT ========

@bot.command(aliases=['p'])
async def play(ctx, *, termo):
    if not ctx.author.voice:
        return await ctx.send("❌ Entre em um canal de voz primeiro.")
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    get_guild_queue(ctx.guild.id).append({"termo": termo})

    if not ctx.voice_client.is_playing():
        await tocar_proxima_musica(ctx)
    else:
        await ctx.send(f"✅ Adicionado à fila: `{termo}`")

@bot.command(aliases=['s'])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Pulada!")

@bot.command()
async def stop(ctx):
    get_guild_queue(ctx.guild.id).clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("🛑 Parado.")

# ======== SISTEMA DE CARGOS ========

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
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(str(reaction.emoji))
        role = discord.utils.get(reaction.message.guild.roles, name=role_name)
        member = await reaction.message.guild.fetch_member(user.id)
        if role: await member.add_roles(role)

@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: return
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(str(reaction.emoji))
        role = discord.utils.get(reaction.message.guild.roles, name=role_name)
        member = await reaction.message.guild.fetch_member(user.id)
        if role: await member.remove_roles(role)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    if message.channel.name == "promos":
        keywords = {"@monitor": "monitor", "@teclado": "teclado", "@gabinete": "gabinete", "sorteio": "Sorteio"}
        for kw, rn in keywords.items():
            if kw in message.content.lower():
                role = discord.utils.get(message.guild.roles, name=rn)
                if role: await message.channel.send(f"<@&{role.id}>")

@bot.event
async def on_ready():
    print(f'✅ Bot online: {bot.user}')

bot.run(Meu_token)