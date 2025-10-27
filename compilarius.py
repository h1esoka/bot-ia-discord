import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

# Carrega token
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("Defina DISCORD_TOKEN no ambiente.")

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

CANAL_ID = 1423834073776001075

# Consulta ao Ollama
async def query_ollama_stream(prompt: str):
    process = await asyncio.create_subprocess_exec(
        "ollama", "run", "wizardcoder",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    process.stdin.write((prompt + "\n").encode())
    await process.stdin.drain()
    process.stdin.close()

    async for line in process.stdout:
        decoded = line.decode().strip()
        if decoded:
            yield decoded
    await process.wait()

# Envio gradual da resposta
async def send_human_like(channel, content, sent_msg=None):
    if not content.strip():
        return
    if not sent_msg:
        sent_msg = await channel.send("🔹 Gerando resposta...")
    await sent_msg.edit(content=content[:2000])
    return sent_msg

# Comando de artigos
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
        description="Recursos gratuitos encontrados:",
        color=discord.Color.blurple()
    )
    for link in links:
        embed.add_field(name="Abrir link", value=f"[Clique aqui]({link})", inline=False)
    await ctx.send(embed=embed)

# Evento de mensagem
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)
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

bot.run(DISCORD_TOKEN)

