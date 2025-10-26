import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

# ---------- Variáveis de ambiente ----------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("Defina DISCORD_TOKEN no ambiente.")

# ---------- Configuração do bot ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Canal permitido ----------
CANAL_ID = 1423834073776001075

# ---------- Função para consultar Ollama ----------
async def query_ollama_stream(prompt: str):
    """
    Stream do Ollama WizardCoder local via subprocesso.
    """
    process = await asyncio.create_subprocess_exec(
        "ollama", "run", "wizardcoder",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Envia prompt
    process.stdin.write((prompt + "\n").encode())
    await process.stdin.drain()
    process.stdin.close()

    # Lê linha por linha
    async for line in process.stdout:
        decoded = line.decode().strip()
        if decoded:
            yield decoded

    await process.wait()

# ---------- Função para enviar resposta parcial ----------
async def send_human_like(channel, content, sent_msg=None):
    """
    Envia a resposta aos poucos, simulando digitação.
    """
    if not content.strip():
        return

    if not sent_msg:
        sent_msg = await channel.send("🔹 Gerando resposta...")

    # Atualiza a mensagem existente
    await sent_msg.edit(content=content[:2000])  # Discord limita a 2000 chars
    return sent_msg

# ---------- Comando de artigos gratuitos ----------
@bot.command(name="recursos")
async def recursos(ctx, *, termo: str):
    if ctx.channel.id != CANAL_ID:
        return
    links = [
        f"https://dev.to/search?q={termo.replace(' ', '+')}",
        f"https://www.freecodecamp.org/news/search/?query={termo.replace(' ', '+')}",
        f"https://www.geeksforgeeks.org/?s={termo.replace(' ', '+')}"
    ]
    embed = discord.Embed(
        title=f"Artigos gratuitos sobre '{termo}'",
        description="Aqui estão alguns recursos online gratuitos:",
        color=discord.Color.blurple()
    )
    for link in links:
        embed.add_field(name="Abrir link", value=f"[Clique aqui]({link})", inline=False)
    await ctx.send(embed=embed)

# ---------- Evento de mensagens ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    # Responde apenas no canal autorizado
    if message.channel.id != CANAL_ID:
        return

    prompt = message.content.strip()
    if not prompt:
        return

    sent_msg = None
    resposta_parcial = ""
    try:
        async for chunk in query_ollama_stream(prompt):
            resposta_parcial += chunk + " "
            sent_msg = await send_human_like(message.channel, resposta_parcial, sent_msg)
    except Exception as e:
        await message.channel.send(f"❌ Erro ao gerar resposta: {e}")

# ---------- Rodar bot ----------
bot.run(DISCORD_TOKEN)
