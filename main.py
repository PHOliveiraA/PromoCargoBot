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

# ======== SISTEMA DE FILA (ESSENCIAL PARA NÃO DAR NAMEERROR) ========
musica_filas = {}

def get_guild_queue(guild):
    if guild.id not in musica_filas:
        musica_filas[guild.id] = []
    return musica_filas[guild.id]

import re # Adicione este import no topo do seu arquivo

# ======== OPÇÕES DE PESQUISA (CONFIGURAÇÃO RESILIENTE) ========
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'source_address': '0.0.0.0',
    'force_ipv4': True,
    # Cliente Android costuma liberar o título mesmo quando bloqueia o streaming
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# ======== LÓGICA DE EXTRAÇÃO E FALLBACK ========
async def obter_audio(url_ou_termo):
    titulo_limpo = None
    url_direta = None

    # 1. TENTATIVA YOUTUBE (PEGAR TÍTULO E ÁUDIO)
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Se for link, tenta extrair info. Se for busca, pesquisa no YT.
            alvo = url_ou_termo if url_ou_termo.startswith("http") else f"ytsearch1:{url_ou_termo}"
            
            # process=False tenta pegar metadados sem disparar o bloqueio de streaming pesado
            info = await asyncio.to_thread(ydl.extract_info, alvo, download=False)
            
            if info and 'entries' in info:
                info = info['entries'][0]
            
            if info:
                titulo_limpo = info.get('title')
                url_direta = info.get('url') # Link do áudio
    except Exception as e:
        print(f"DEBUG: YouTube falhou totalmente: {e}")

    # 2. TRATAMENTO DE NOME (CORREÇÃO DO SEU ERRO)
    # Se o YouTube bloqueou o áudio, mas temos o título, usamos o título.
    # Se não temos o título e é um link, tentamos extrair o ID do vídeo para não buscar a URL pura.
    busca_soundcloud = titulo_limpo
    
    if not busca_soundcloud or busca_soundcloud.startswith("http"):
        if "youtube.com" in url_ou_termo or "youtu.be" in url_ou_termo:
            # Tenta extrair o ID do vídeo via Regex para uma busca genérica se o título falhar
            vid_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url_ou_termo)
            busca_soundcloud = vid_id.group(1) if vid_id else url_ou_termo
        else:
            busca_soundcloud = url_ou_termo

    # 3. FALLBACK SOUNDCLOUD (SE O ÁUDIO DO YT FALHOU)
    if not url_direta:
        print(f"⚠️ YouTube bloqueou o áudio. Buscando '{busca_soundcloud}' no SoundCloud...")
        try:
            sc_opts = {'format': 'bestaudio', 'quiet': True}
            with yt_dlp.YoutubeDL(sc_opts) as ydl_sc:
                # PESQUISA POR NOME (scsearch), NUNCA POR URL DO YOUTUBE
                info_sc = await asyncio.to_thread(ydl_sc.extract_info, f"scsearch1:{busca_soundcloud}", download=False)
                if info_sc and 'entries' in info_sc and len(info_sc['entries']) > 0:
                    res = info_sc['entries'][0]
                    url_direta = res['url']
                    titulo_limpo = res.get('title', busca_soundcloud)
        except Exception as e_sc:
            print(f"❌ Erro SoundCloud: {e_sc}")

    return url_direta, titulo_limpo

# ======== FUNÇÃO TOCAR (CORRIGIDA) ========
async def tocar_proxima_musica(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue: return

    musica_atual = queue.pop(0)
    termo = musica_atual["termo"]
    msg_status = await ctx.send(f"🔍 Buscando: `{termo}`...")

    url_final, titulo_final = await obter_audio(termo)

    if not url_final:
        await msg_status.edit(content=f"❌ Não foi possível carregar: `{termo}`. Verifique se o vídeo não tem restrição de idade.")
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
        await msg_status.edit(content="❌ Erro ao iniciar o player.")
        await tocar_proxima_musica(ctx)

# ======== COMANDOS DE MÚSICA ========
@bot.command(aliases=['p'])
async def play(ctx, *, termo):
    if not ctx.author.voice:
        return await ctx.send("❌ Você precisa estar em um canal de voz.")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    queue = get_guild_queue(ctx.guild)
    queue.append({"termo": termo})

    if not ctx.voice_client.is_playing():
        await tocar_proxima_musica(ctx)
    else:
        await ctx.send(f"✅ Adicionado à fila: `{termo}`")

@bot.command(aliases=['s'])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Música pulada!")
    else:
        await ctx.send("❌ Nada tocando agora.")

@bot.command()
async def stop(ctx):
    get_guild_queue(ctx.guild).clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("🛑 Parado e desconectado.")

@bot.command(aliases=['q'])
async def queue(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue:
        return await ctx.send("🎵 Fila vazia.")
    msg = "\n".join([f"{i+1}. {m['termo']}" for i, m in enumerate(queue[:10])])
    await ctx.send(f"📜 **Fila atual:**\n{msg}")

# ======== SISTEMA DE CARGOS E MONITORAMENTO ========
async def clear_old_setup_messages(channel):
    async for message in channel.history(limit=100):
        if message.author == bot.user and "Reaja com os emojis abaixo" in message.content:
            await message.delete()

@bot.command()
async def setup(ctx):
    if ctx.channel.name == "cargo-de-promoção-aqui":
        await clear_old_setup_messages(ctx.channel)
        message_text = "Reaja com os emojis abaixo para obter cargos:\n"
        for emoji, role in emoji_to_role.items():
            message_text += f"{emoji} - {role}\n"
        message = await ctx.send(message_text)
        for emoji in emoji_to_role.keys():
            await message.add_reaction(emoji)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user: return
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(reaction.emoji)
        role = discord.utils.get(reaction.message.guild.roles, name=role_name)
        if role:
            member = await reaction.message.guild.fetch_member(user.id)
            await member.add_roles(role)

@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: return
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(reaction.emoji)
        role = discord.utils.get(reaction.message.guild.roles, name=role_name)
        if role:
            member = await reaction.message.guild.fetch_member(user.id)
            await member.remove_roles(role)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    if message.channel.name == "promos":
        keyword_responses = {
            "@monitor": "monitor", "@teclado": "teclado", "@gabinete": "gabinete",
            "@cupom": "cupom", "@placa de vídeo": "placa de vídeo", "@filtro de linha": "filtro de linha",
            "@memória": "memória", "@fonte": "fonte", "@smartphone": "smartphone",
            "@microfone": "microfone", "@acessórios": "acessórios", "@placa mãe": "placa mãe",
            "@air / water / fan cooler": "cooler", "@processador": "processador", "sorteio": "Sorteio"
        }
        content_lower = message.content.lower()
        for keyword, role_name in keyword_responses.items():
            if keyword in content_lower:
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role: await message.channel.send(f"<@&{role.id}>")

@bot.event
async def on_ready():
    print(f'✅ Bot online como {bot.user} (Streaming Bypass Ativo)')

# ======== EXECUTAR ========
try:
    bot.run(Meu_token)
except Exception as e:
    print(f"Erro ao rodar: {e}")