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

# ======== FUNÇÕES AUXILIARES (SETUP) ========
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
    # Certifique-se que este ID é o do canal correto onde o setup roda
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

# ======== NOVA FUNÇÃO OBTER ÁUDIO (VIA PROXY PIPED) ========
async def obter_audio(url_ou_termo):
    # --- ESTÁGIO 1: Redirecionar para Piped ---
    # Em vez de ir direto no YouTube, convertemos o link para um servidor Piped público.
    # Isso faz com que o bloqueio de IP do YouTube não afete você diretamente.
    
    target_url = url_ou_termo
    
    # Se for link do YouTube, extrai o ID e monta link Piped
    if "youtube.com" in url_ou_termo or "youtu.be" in url_ou_termo:
        video_id = None
        if "v=" in url_ou_termo:
            video_id = url_ou_termo.split("v=")[1].split("&")[0]
        elif "youtu.be" in url_ou_termo:
            video_id = url_ou_termo.split("/")[-1].split("?")[0]
            
        if video_id:
            target_url = f"https://piped.video/watch?v={video_id}"

    # Se não for link nenhum, assume que é pesquisa e pesquisa no Piped
    elif not url_ou_termo.startswith("http"):
        # Pesquisa simples no Piped
        target_url = f"https://piped.video/results?search_query={url_ou_termo.replace(' ', '+')}"

    # --- ESTÁGIO 2: Configuração do yt-dlp ---
# ======== FUNÇÃO OBTER ÁUDIO (STREAMING INTELIGENTE - TENTA TUDO) ========
# ======== FUNÇÃO OBTER ÁUDIO (SELEÇÃO INTELIGENTE DE CLIENTES) ========
async def obter_audio(url_ou_termo):
    tem_cookies = os.path.exists("cookies.txt")
    
    # SEGREDO: Separamos os clientes.
    # Com cookies: Usamos apenas os baseados em navegador (web, mweb, tv).
    # Sem cookies: Tentamos os nativos (android, ios) que às vezes funcionam sem login.
    if tem_cookies:
        CLIENTES = ['web', 'mweb', 'tv_embedded']
        print("🍪 Cookies detectados: Usando clientes WEB.")
    else:
        CLIENTES = ['android', 'ios', 'web', 'tv_embedded']
        print("⚠️ Sem cookies: Tentando clientes NATIVOS primeiro.")

    def buscar_em_background():
        base_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'geo_bypass': True,
            'source_address': '0.0.0.0',
            'force_ipv4': True,
            'ignoreconfig': True,
            'cookiefile': 'cookies.txt' if tem_cookies else None,
            # Adiciona um User-Agent genérico para tentar enganar bloqueios simples
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        if not tem_cookies:
            base_opts['no_cookies'] = True

        for cliente in CLIENTES:
            print(f"🔄 Tentando background com: {cliente}...")
            current_opts = base_opts.copy()
            current_opts['extractor_args'] = {'youtube': {'player_client': [cliente]}}
            
            try:
                with yt_dlp.YoutubeDL(current_opts) as ydl:
                    if "youtube.com" in url_ou_termo or "youtu.be" in url_ou_termo:
                        info = ydl.extract_info(url_ou_termo, download=False)
                    else:
                        res = ydl.extract_info(f"ytsearch:{url_ou_termo}", download=False)
                        info = res['entries'][0] if 'entries' in res else None

                if info and info.get('url'):
                     print(f"✅ Sucesso background com {cliente}!")
                     return info['url'], info.get('title', 'Música')
            except Exception:
                continue
        return None, None

    return await asyncio.to_thread(buscar_em_background)

# ======== FUNÇÃO TOCAR (STREAMING ROBUSTO) ========
async def tocar_proxima_musica(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue:
        return

    musica_atual = queue.pop(0)
    termo_busca = musica_atual["termo"]

    msg_processando = await ctx.send(f"🔄 Processando: `{termo_busca}`...")

    try:
        # Agora retorna uma URL de internet, não um arquivo local
        audio_url, titulo_real = await obter_audio(termo_busca)
    except Exception as e:
        await msg_processando.edit(content=f"❌ Erro crítico: {e}")
        await tocar_proxima_musica(ctx)
        return

    if not audio_url:
        await msg_processando.edit(content="❌ Falha ao obter link de streaming.")
        await tocar_proxima_musica(ctx)
        return

    if not ctx.voice_client or not ctx.voice_client.is_connected():
        try:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                 await msg_processando.edit(content="❌ Entre em um canal de voz primeiro.")
                 return
        except Exception:
             return

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        ctx.voice_client.stop()

    # Opções do FFmpeg para aguentar quedas de conexão do YouTube
    ffmpeg_options = {
        'before_options': (
            '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
            '-reconnect_at_eof 1 -http_persistent 0'
        ),
        'options': '-vn'
    }

    def after_playing(error):
        if error:
            print(f"Erro no streaming: {error}")
        asyncio.run_coroutine_threadsafe(tocar_proxima_musica(ctx), bot.loop)

    try:
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        ctx.voice_client.play(source, after=after_playing)
        await msg_processando.edit(content=f"🎶 Tocando agora: **{titulo_real}**")
    except Exception as e:
        await msg_processando.edit(content=f"❌ Erro ao iniciar player: {e}")
        await tocar_proxima_musica(ctx)

# ======== COMANDOS DE MÚSICA ========
@bot.command()
async def play(ctx, *, termo):
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await ctx.send("❌ Você precisa estar em um canal de voz.")
        return

    if not ctx.voice_client:
        await voice_channel.connect()

    # Adiciona à fila apenas o termo/URL. Deixa para processar na hora de tocar.
    # Isso deixa o comando !play muito mais rápido.
    queue = get_guild_queue(ctx.guild)
    queue.append({"termo": termo})

    if not ctx.voice_client.is_playing():
        await tocar_proxima_musica(ctx)
    else:
        await ctx.send(f"✅ Adicionado à fila: `{termo}`")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() # Isso aciona o 'after' do play, chamando a próxima
        await ctx.send("⏭️ Pulado!")
    else:
        await ctx.send("❌ Nada tocando para pular.")

@bot.command()
async def stop(ctx):
    queue = get_guild_queue(ctx.guild)
    queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("🛑 Parado e desconectado.")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Pausado.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Retomado.")

@bot.command()
async def queue(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue:
        await ctx.send("🎵 Fila vazia.")
    else:
        # Mostra apenas os primeiros 10 para não flodar o chat
        msg = "\n".join([f"{i+1}. {m['termo']}" for i, m in enumerate(queue[:10])])
        if len(queue) > 10:
            msg += f"\n... e mais {len(queue)-10} na fila."
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