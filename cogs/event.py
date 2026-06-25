import discord
from discord.ext import commands
import string
import time
import asyncio
import hexlogger

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._nick_cooldowns = {}

    def sanitize_name(self, name: str, config: dict) -> tuple[str, list[str]]:
        if not name:
            return "", []
            
        applied_rules = []
        cleaned = name
        
        if config.get("strict_ascii", False):
            ascii_cleaned = cleaned.encode("ascii", errors="ignore").decode("ascii")
            if len(ascii_cleaned) < len(cleaned):
                cleaned = ascii_cleaned
                applied_rules.append("Strict ASCII (removed non-ASCII characters)")
                
        if config.get("block_leading_symbol", True) or config.get("auto_dehoist", True):
            hoisting_chars = string.punctuation + " "
            stripped = cleaned.lstrip(hoisting_chars)
            
            while stripped and not stripped[0].isalnum():
                stripped = stripped[1:]
                
            if len(stripped) < len(cleaned):
                cleaned = stripped
                applied_rules.append("Auto-Dehoist (removed leading symbols)")

        if config.get("sanitize_enabled", True):
            stripped_all = "".join(c for c in cleaned if c.isalnum() or c.isspace())
            if len(stripped_all) < len(cleaned):
                cleaned = stripped_all
                applied_rules.append("Sanitized (removed all symbols)")
                
        cleaned = " ".join(cleaned.split())
        
        if not cleaned:
            return "", applied_rules
            
        return cleaned[:32], applied_rules

    async def check_and_sanitize_member(self, member: discord.Member, trigger: str):
        if member.bot or member.id == member.guild.owner_id:
            return
            
        guild_id = str(member.guild.id)
        config = self.bot.guild_configs.get(guild_id, {})

        if member.id in config.get("whitelist", []):
            return
        
        if not config.get("sanitize_enabled", True):
            return
            
        current_name = member.display_name
        sanitized_name, applied_rules = self.sanitize_name(current_name, config)
        
        if not sanitized_name or current_name == sanitized_name:
            return
            
        try:
            await member.edit(nick=sanitized_name, reason=f"Auto-sanitized name: {', '.join(applied_rules)}")
            hexlogger.info(f"Auto-sanitized {member} ({member.id}) in guild {member.guild.id}. Rules: {applied_rules}")
            
            log_channel_id = config.get("log_channel_id")
            if log_channel_id:
                channel = member.guild.get_channel(log_channel_id)
                if channel:
                    from cogs.embed import EmbedHelper
                    embed = EmbedHelper.auto_sanitized_embed(
                        member=member,
                        old_name=current_name,
                        new_nickname=sanitized_name,
                        reason=", ".join(applied_rules)
                    )
                    await channel.send(embed=embed)
        except discord.Forbidden:
            hexlogger.warning(f"Failed to change nickname of {member} ({member.id}) due to lack of permissions.")
            log_channel_id = config.get("log_channel_id")
            if log_channel_id:
                channel = member.guild.get_channel(log_channel_id)
                if channel:
                    await channel.send(
                        f"⚠️ **Permission Error**: Could not auto-sanitize name of {member.mention} (`{member.display_name}`). "
                        "Please check that the bot's role is positioned higher than this user's highest role."
                    )
        except Exception as e:
            hexlogger.error(f"Error during auto-sanitization of {member.id}: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.check_and_sanitize_member(member, "join")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            await self.check_and_sanitize_member(after, "update")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.content.startswith("."):
            return

        guild_id = str(message.guild.id)
        config = self.bot.guild_configs.get(guild_id, {})
        request_channel_id = config.get("request_channel_id")

        if request_channel_id and message.channel.id == request_channel_id:
            content = message.content.strip()
            
            async def safe_reply(reply_content=None, embed=None):
                try:
                    reply_msg = await message.reply(content=reply_content, embed=embed)
                    if not embed:
                        await reply_msg.delete(delay=5)
                except discord.HTTPException:
                    mention = f"{message.author.mention}, " if reply_content else ""
                    try:
                        fallback = await message.channel.send(content=f"{mention}{reply_content}" if reply_content else None, embed=embed)
                        if not embed:
                            await fallback.delete(delay=5)
                    except discord.HTTPException:
                        pass


            if content.lower() in ("reset", "clear"):
                if message.author.id == message.guild.owner_id:
                    await safe_reply("❌ Server Owner's nickname cannot be managed by the bot.")
                    return

                try:
                    await message.author.edit(nick=None, reason="User requested nickname reset via nickname channel")
                    from cogs.embed import EmbedHelper
                    embed = EmbedHelper.reset_embed()
                    await safe_reply(embed=embed)
                except discord.Forbidden:
                    await safe_reply("❌ I do not have permission to change your nickname. Make sure my role is above yours.")
                except Exception as e:
                    hexlogger.error(f"Failed to reset nickname: {e}")
                return

            cooldown_key = f"{guild_id}:{message.author.id}"
            now = time.time()
            last_used = self._nick_cooldowns.get(cooldown_key, 0)
            remaining = 15 - (now - last_used)
            if remaining > 0:
                await safe_reply(f"⏳ Please wait **{int(remaining)+1}s** before requesting another nickname.")
                return
            self._nick_cooldowns[cooldown_key] = now

            nickname_cog = self.bot.get_cog("NicknameCog")
            if nickname_cog:
                async def reply_func(reply_content=None, ephemeral=True, defer=False, follow_up=False, embed=None):
                    if not defer:
                        await safe_reply(reply_content, embed=embed)
                
                await nickname_cog.handle_nickname_request(
                    member=message.author,
                    guild=message.guild,
                    nickname=content,
                    reply_func=reply_func
                )

async def setup(bot):
    await bot.add_cog(EventCog(bot))
