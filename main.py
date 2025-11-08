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

# ======== NOVA FUNÇÃO OBTER ÁUDIO (COM BYPASS MELHORADO) ========
async def obter_audio(url_ou_termo):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,  # Permite falhar e tentar o fallback
        'geo_bypass': True,
        'source_address': '0.0.0.0',
        'force_ipv4': True,
        # --- Travas de Privacidade/Segurança ---
        'no_cookies': True,
        'no_cache_dir': True,
        'ignoreconfig': True,
        # --- Tentativa de Bypass de Cliente ---
        # Tenta voltar para o android se o web_embedded estiver falhando com Error 153
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = None
        # Tenta extrair diretamente primeiro
        try:
            # Se não for um link, ele já vai falhar aqui e cair no except (que é o que queremos para buscas)
            info = ydl.extract_info(url_ou_termo, download=False)
        except Exception:
            pass

        # Se falhou ou veio vazio (bloqueio do YouTube frequentemente retorna None em vez de erro)
        if not info:
            print(f"Tentativa direta falhou para '{url_ou_termo}', tentando ytsearch...")
            try:
                # Força uma pesquisa. Isso ajuda a contornar bloqueios em links diretos.
                busca = ydl.extract_info(f"ytsearch:{url_ou_termo}", download=False)
                if 'entries' in busca and len(busca['entries']) > 0:
                    info = busca['entries'][0]
            except Exception as e:
                print(f"Erro fatal no ytsearch: {e}")
                return None, None

        if not info:
            return None, None

        # Garante que temos uma URL jogável
        url_audio = info.get('url')
        if not url_audio:
             # Fallback: procura nos formatos se a URL principal estiver vazia
             for f in info.get('formats', []):
                 if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                     url_audio = f['url']
                     break

        return url_audio, info.get('title', 'Música desconhecida')

# ======== FUNÇÃO DE TOCAR MÚSICA ========
async def tocar_proxima_musica(ctx):
    queue = get_guild_queue(ctx.guild)
    if not queue:
        # await ctx.send("🎵 Fila de músicas vazia.") # Opcional: avisar quando acaba
        return

    musica_atual = queue.pop(0)
    termo_busca = musica_atual["termo"] # Pode ser URL ou nome da música

    # Avisa que está processando (útil porque o yt-dlp pode demorar um pouco)
    msg_processando = await ctx.send(f"🔄 Processando: `{termo_busca}`...")

    try:
        audio_url, titulo_real = await obter_audio(termo_busca)
    except Exception as e:
        await msg_processando.edit(content=f"❌ Erro crítico ao obter áudio: {e}")
        await tocar_proxima_musica(ctx) # Tenta a próxima
        return

    if not audio_url:
        await msg_processando.edit(content=f"❌ Não foi possível tocar: `{termo_busca}` (Bloqueado pelo YouTube ou não encontrado).")
        await tocar_proxima_musica(ctx) # Tenta a próxima
        return

    # Conecta se necessário
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        try:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                 await msg_processando.edit(content="❌ Você não está em um canal de voz.")
                 return
        except Exception:
            return

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        ctx.voice_client.stop()

    try:
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
        await msg_processando.edit(content=f"🎶 Tocando agora: **{titulo_real}**")
    except Exception as e:
        await msg_processando.edit(content=f"❌ Erro ao iniciar reprodução: {e}")
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