import discord
from discord.ext import commands
from discord import app_commands
import hexlogger
from typing import Optional
from cogs.embed import EmbedHelper

class NicknameApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_nick_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_request(interaction, approve=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="reject_nick_btn")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_request(interaction, approve=False)

    async def process_request(self, interaction: discord.Interaction, approve: bool):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You lack permissions (Administrator) to manage this request.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        message_id = str(interaction.message.id)
        
        config = interaction.client.guild_configs.get(guild_id, {})
        requests = config.get("requests", {})
        
        if message_id not in requests:
            await interaction.response.send_message("⚠️ Request not found or has already been processed.", ephemeral=True)
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            return

        request_data = requests[message_id]
        member_id = request_data["user_id"]
        requested_nickname = request_data["nickname"]
        
        member = interaction.guild.get_member(member_id)
        if not member:
            await interaction.response.send_message("⚠️ The member who requested this nickname is no longer in the server.", ephemeral=True)
            requests.pop(message_id, None)
            interaction.client.save_config()
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            return

        await interaction.response.defer()
        
        event_cog = interaction.client.get_cog("EventCog")
        log_channel_id = config.get("log_channel_id")
        
        if approve:
            is_whitelisted = member_id in config.get("whitelist", [])
            if event_cog and not is_whitelisted:
                target_name, _ = event_cog.sanitize_name(requested_nickname, config)
            else:
                target_name = requested_nickname
                
            try:
                await member.edit(nick=target_name, reason=f"Nickname request approved by {interaction.user}")
                
                embed = EmbedHelper.approved_embed(member, target_name, interaction.user.mention)
                for item in self.children:
                    item.disabled = True
                await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
                
                if log_channel_id:
                    log_channel = interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(embed=embed)
                        
                try:
                    dm_embed = EmbedHelper.dm_approved_embed(interaction.guild.name, target_name)
                    await member.send(embed=dm_embed)
                except discord.HTTPException:
                    pass
            except discord.Forbidden:
                await interaction.followup.send("❌ Failed to update nickname. Please ensure my role is higher than the member's highest role.", ephemeral=True)
                return
        else:
            embed = EmbedHelper.rejected_embed(member, requested_nickname, interaction.user.mention)
            for item in self.children:
                item.disabled = True
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
            
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)
                    
            try:
                dm_embed = EmbedHelper.dm_rejected_embed(interaction.guild.name, requested_nickname)
                await member.send(embed=dm_embed)
            except discord.HTTPException:
                pass

        requests.pop(message_id, None)
        interaction.client.save_config()


class NicknameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="logs", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def logs_prefix(self, ctx: commands.Context):
        await ctx.send("Use `.logs channel [channel_mention]` to set the logging channel.")

    @logs_prefix.command(name="channel")
    async def logs_channel_prefix(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
            
        self.bot.guild_configs[guild_id]["log_channel_id"] = channel.id
        self.bot.save_config()
        await ctx.reply(f"✅ Logging channel set to {channel.mention}.")

    @commands.group(name="nickname", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def nickname_prefix(self, ctx: commands.Context):
        await ctx.send("Use `.nickname channel [channel_mention]` to set the nickname requests/interaction channel.")

    @nickname_prefix.command(name="channel")
    async def nickname_channel_prefix(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
            
        self.bot.guild_configs[guild_id]["request_channel_id"] = channel.id
        self.bot.save_config()
        await ctx.reply(f"✅ Nickname requests/interaction channel set to {channel.mention}.")

    @commands.group(name="setup", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def setup_prefix(self, ctx: commands.Context):
        await ctx.send(
            "⚙️ **Bot Configuration Subcommands:**\n"
            "• `.setup auto_approve [on/off]` - Toggle automatic nickname approvals\n"
            "• `.setup filter [sanitize: on/off] [ascii: on/off] [leading: on/off] [dehoist: on/off]` - Configure name filters\n"
            "• `.setup status` - View current configuration status"
        )

    @setup_prefix.command(name="auto_approve")
    async def setup_auto_approve_prefix(self, ctx: commands.Context, status: str):
        guild_id = str(ctx.guild.id)
        enabled = status.lower() in ("on", "true", "yes", "enable", "enabled")
        
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
            
        self.bot.guild_configs[guild_id]["auto_approve"] = enabled
        self.bot.save_config()
        status_text = "enabled (requests auto-apply instantly)" if enabled else "disabled (requires admin review)"
        await ctx.reply(f"✅ Auto-approve system has been **{status_text}**.")

    @setup_prefix.command(name="filter")
    async def setup_filter_prefix(
        self, 
        ctx: commands.Context, 
        sanitize: Optional[str] = None,
        ascii_only: Optional[str] = None,
        leading: Optional[str] = None,
        dehoist: Optional[str] = None
    ):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
            
        guild_config = self.bot.guild_configs[guild_id]
        
        def parse_val(v):
            if v is None: return None
            return v.lower() in ("on", "true", "yes", "enable", "enabled")
            
        changes = []
        if sanitize is not None:
            val = parse_val(sanitize)
            guild_config["sanitize_enabled"] = val
            changes.append(f"sanitize_enabled={val}")
        if ascii_only is not None:
            val = parse_val(ascii_only)
            guild_config["strict_ascii"] = val
            changes.append(f"strict_ascii={val}")
        if leading is not None:
            val = parse_val(leading)
            guild_config["block_leading_symbol"] = val
            changes.append(f"block_leading_symbol={val}")
        if dehoist is not None:
            val = parse_val(dehoist)
            guild_config["auto_dehoist"] = val
            changes.append(f"auto_dehoist={val}")
            
        if not changes:
            await ctx.reply("❌ Specify at least one configuration value, e.g. `.setup filter on on`")
            return
            
        self.bot.save_config()
        await ctx.reply(f"✅ Filter configuration updated: {', '.join(changes)}")

    @setup_prefix.command(name="status")
    async def setup_status_prefix(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        config = self.bot.guild_configs.get(guild_id, self.bot.get_default_guild_config())
        
        log_channel = None
        log_channel_id = config.get("log_channel_id")
        if log_channel_id:
            log_channel = ctx.guild.get_channel(log_channel_id)
            
        request_channel = None
        request_channel_id = config.get("request_channel_id")
        if request_channel_id:
            request_channel = ctx.guild.get_channel(request_channel_id)
            
        embed = EmbedHelper.status_embed(ctx.guild.name, config, log_channel, request_channel)
        await ctx.reply(embed=embed)

    logs_group = app_commands.Group(
        name="logs",
        description="Configure logging settings",
        default_permissions=discord.Permissions(administrator=True)
    )

    @logs_group.command(name="channel", description="Set the channel where name updates/actions are logged")
    @app_commands.describe(channel="The text channel where log embeds will be sent")
    async def logs_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
        self.bot.guild_configs[guild_id]["log_channel_id"] = channel.id
        self.bot.save_config()
        await interaction.response.send_message(f"✅ Logging channel set to {channel.mention}.", ephemeral=True)

    nickname_group = app_commands.Group(
        name="nickname",
        description="Configure nickname request settings",
        default_permissions=discord.Permissions(administrator=True)
    )

    @nickname_group.command(name="channel", description="Set the channel where users request nickname changes")
    @app_commands.describe(channel="The text channel where users type desired names or manual request prompts are sent")
    async def nickname_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
        self.bot.guild_configs[guild_id]["request_channel_id"] = channel.id
        self.bot.save_config()
        await interaction.response.send_message(f"✅ Nickname requests/interaction channel set to {channel.mention}.", ephemeral=True)

    setup_group = app_commands.Group(
        name="setup", 
        description="Configure nickname bot settings",
        default_permissions=discord.Permissions(administrator=True)
    )

    @setup_group.command(name="auto_approve", description="Toggle auto-approval for nickname changes")
    @app_commands.describe(enabled="True to auto-approve requests instantly, False to require admin review")
    async def setup_auto_approve(self, interaction: discord.Interaction, enabled: bool):
        guild_id = str(interaction.guild_id)
        
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
            
        self.bot.guild_configs[guild_id]["auto_approve"] = enabled
        self.bot.save_config()
        
        status_text = "enabled (requests auto-apply instantly)" if enabled else "disabled (requires admin review)"
        await interaction.response.send_message(f"✅ Auto-approve system has been **{status_text}**.", ephemeral=True)

    @setup_group.command(name="filter", description="Configure name sanitization/blocking filters")
    @app_commands.describe(
        sanitize_enabled="Enable/Disable nickname filtering",
        strict_ascii="Force names to only use ASCII characters (strips emojis/special unicode)",
        block_leading_symbol="Prevent leading symbols/punctuation in nicknames",
        auto_dehoist="Automatically strip leading hoisting symbols"
    )
    async def setup_filter(
        self, 
        interaction: discord.Interaction, 
        sanitize_enabled: Optional[bool] = None,
        strict_ascii: Optional[bool] = None,
        block_leading_symbol: Optional[bool] = None,
        auto_dehoist: Optional[bool] = None
    ):
        guild_id = str(interaction.guild_id)
        
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
            
        guild_config = self.bot.guild_configs[guild_id]
        
        changes = []
        if sanitize_enabled is not None:
            guild_config["sanitize_enabled"] = sanitize_enabled
            changes.append(f"sanitize_enabled={sanitize_enabled}")
        if strict_ascii is not None:
            guild_config["strict_ascii"] = strict_ascii
            changes.append(f"strict_ascii={strict_ascii}")
        if block_leading_symbol is not None:
            guild_config["block_leading_symbol"] = block_leading_symbol
            changes.append(f"block_leading_symbol={block_leading_symbol}")
        if auto_dehoist is not None:
            guild_config["auto_dehoist"] = auto_dehoist
            changes.append(f"auto_dehoist={auto_dehoist}")
            
        if not changes:
            await interaction.response.send_message("❌ No parameters were specified to change.", ephemeral=True)
            return
            
        self.bot.save_config()
        await interaction.response.send_message(f"✅ Filter configuration updated: {', '.join(changes)}", ephemeral=True)

    @setup_group.command(name="status", description="Display the current configuration settings")
    async def setup_status(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        config = self.bot.guild_configs.get(guild_id, self.bot.get_default_guild_config())
        
        log_channel = None
        log_channel_id = config.get("log_channel_id")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            
        request_channel = None
        request_channel_id = config.get("request_channel_id")
        if request_channel_id:
            request_channel = interaction.guild.get_channel(request_channel_id)
            
        embed = EmbedHelper.status_embed(interaction.guild.name, config, log_channel, request_channel)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    whitelist_group = app_commands.Group(
        name="whitelist",
        description="Manage whitelisted users who bypass symbol filtering",
        default_permissions=discord.Permissions(administrator=True)
    )

    @whitelist_group.command(name="add", description="Whitelist a user to bypass symbol filtering")
    @app_commands.describe(user="The user to whitelist")
    async def whitelist_add(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
        config = self.bot.guild_configs[guild_id]
        if "whitelist" not in config:
            config["whitelist"] = []
        if user.id in config["whitelist"]:
            await interaction.response.send_message(f"⚠️ {user.mention} is already whitelisted.", ephemeral=True)
            return
        config["whitelist"].append(user.id)
        self.bot.save_config()
        await interaction.response.send_message(f"✅ {user.mention} has been added to the whitelist. Symbol filtering will be bypassed for this user.", ephemeral=True)

    @whitelist_group.command(name="remove", description="Remove a user from the whitelist")
    @app_commands.describe(user="The user to remove from whitelist")
    async def whitelist_remove(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = str(interaction.guild_id)
        config = self.bot.guild_configs.get(guild_id, {})
        wl = config.get("whitelist", [])
        if user.id not in wl:
            await interaction.response.send_message(f"⚠️ {user.mention} is not in the whitelist.", ephemeral=True)
            return
        wl.remove(user.id)
        self.bot.save_config()
        await interaction.response.send_message(f"✅ {user.mention} has been removed from the whitelist.", ephemeral=True)

    @whitelist_group.command(name="list", description="View all whitelisted users")
    async def whitelist_list(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        config = self.bot.guild_configs.get(guild_id, {})
        wl = config.get("whitelist", [])
        if not wl:
            await interaction.response.send_message("📋 No users are currently whitelisted.", ephemeral=True)
            return
        lines = [f"• <@{uid}> (`{uid}`)" for uid in wl]
        embed = discord.Embed(
            title="📋 Whitelisted Users",
            color=EmbedHelper.COLOR_INFO,
            description="\n".join(lines)
        )
        embed.set_footer(text=f"Total: {len(wl)} user(s)")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.group(name="whitelist", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def whitelist_prefix(self, ctx: commands.Context):
        await ctx.send("Use `.whitelist add @user`, `.whitelist remove @user`, or `.whitelist list`.")

    @whitelist_prefix.command(name="add")
    async def whitelist_add_prefix(self, ctx: commands.Context, user: discord.Member):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.bot.guild_configs:
            self.bot.guild_configs[guild_id] = self.bot.get_default_guild_config()
        config = self.bot.guild_configs[guild_id]
        if "whitelist" not in config:
            config["whitelist"] = []
        if user.id in config["whitelist"]:
            await ctx.reply(f"⚠️ {user.mention} is already whitelisted.")
            return
        config["whitelist"].append(user.id)
        self.bot.save_config()
        await ctx.reply(f"✅ {user.mention} has been added to the whitelist.")

    @whitelist_prefix.command(name="remove")
    async def whitelist_remove_prefix(self, ctx: commands.Context, user: discord.Member):
        guild_id = str(ctx.guild.id)
        config = self.bot.guild_configs.get(guild_id, {})
        wl = config.get("whitelist", [])
        if user.id not in wl:
            await ctx.reply(f"⚠️ {user.mention} is not in the whitelist.")
            return
        wl.remove(user.id)
        self.bot.save_config()
        await ctx.reply(f"✅ {user.mention} has been removed from the whitelist.")

    @whitelist_prefix.command(name="list")
    async def whitelist_list_prefix(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        config = self.bot.guild_configs.get(guild_id, {})
        wl = config.get("whitelist", [])
        if not wl:
            await ctx.reply("📋 No users are currently whitelisted.")
            return
        lines = [f"• <@{uid}> (`{uid}`)" for uid in wl]
        embed = discord.Embed(
            title="📋 Whitelisted Users",
            color=EmbedHelper.COLOR_INFO,
            description="\n".join(lines)
        )
        embed.set_footer(text=f"Total: {len(wl)} user(s)")
        await ctx.reply(embed=embed)

    async def handle_nickname_request(self, member: discord.Member, guild: discord.Guild, nickname: str, reply_func):
        if len(nickname) > 32:
            await reply_func("❌ Nicknames cannot be longer than 32 characters.", ephemeral=True)
            return

        if len(nickname) < 2:
            await reply_func("❌ Nicknames must be at least 2 characters long.", ephemeral=True)
            return
            
        guild_id = str(guild.id)
        config = self.bot.guild_configs.get(guild_id, self.bot.get_default_guild_config())
        
        if member.id == guild.owner_id:
            await reply_func("❌ Server Owner's nickname cannot be managed by the bot.", ephemeral=True)
            return

        request_channel_id = config.get("request_channel_id")
        if not request_channel_id and not config.get("auto_approve", False):
            await reply_func("⚠️ The admin has not set up a nickname requests channel yet. Cannot process manual request.", ephemeral=True)
            return

        is_whitelisted = member.id in config.get("whitelist", [])

        if is_whitelisted:
            sanitized_nickname = nickname
            applied_rules = []
        else:
            event_cog = self.bot.get_cog("EventCog")
            if event_cog:
                sanitized_nickname, applied_rules = event_cog.sanitize_name(nickname, config)
            else:
                sanitized_nickname = nickname
                applied_rules = []

        if not sanitized_nickname:
            await reply_func("❌ The requested nickname is invalid (contained only forbidden characters).", ephemeral=True)
            return

        log_channel_id = config.get("log_channel_id")
        if config.get("auto_approve", False):
            await reply_func("🔄 Updating nickname...", ephemeral=True, defer=True)
            try:
                await member.edit(nick=sanitized_nickname, reason="Auto-approved nickname request")
                approved_embed = EmbedHelper.approved_embed(member, sanitized_nickname, "System (Auto-Approve)")
                await reply_func(embed=approved_embed, ephemeral=True, follow_up=True)
                
                try:
                    dm_embed = EmbedHelper.dm_approved_embed(guild.name, sanitized_nickname)
                    await member.send(embed=dm_embed)
                except discord.HTTPException:
                    pass
                
                if log_channel_id:
                    channel = guild.get_channel(log_channel_id)
                    if channel:
                        await channel.send(embed=approved_embed)
            except discord.Forbidden:
                pass
            return

        channel = guild.get_channel(request_channel_id)
        if not channel:
            await reply_func("⚠️ Nickname requests channel not found. Please contact an Administrator.", ephemeral=True)
            return
            
        await reply_func("🔄 Submitting request...", ephemeral=True, defer=True)
        
        embed = EmbedHelper.request_embed(member, nickname, sanitized_nickname)
        view = NicknameApprovalView()
        
        try:
            panel_msg = await channel.send(embed=embed, view=view)
            
            if "requests" not in config:
                config["requests"] = {}
            config["requests"][str(panel_msg.id)] = {
                "user_id": member.id,
                "nickname": nickname
            }
            self.bot.save_config()
            
            await reply_func("✅ Your nickname request has been submitted for admin approval.", ephemeral=True, follow_up=True)
        except Exception as e:
            hexlogger.error(f"Failed to send request message: {e}")
            await reply_func("❌ An error occurred while submitting your request. Please try again later.", ephemeral=True, follow_up=True)

    @app_commands.command(name="request_nickname", description="Submit a request to change your server nickname")
    @app_commands.describe(nickname="The new nickname you want to request")
    @app_commands.checks.cooldown(1, 15)
    async def request_nickname(self, interaction: discord.Interaction, nickname: str):
        deferred = False
        async def reply_func(content=None, ephemeral=True, defer=False, follow_up=False, embed=None):
            nonlocal deferred
            if defer:
                await interaction.response.defer(ephemeral=ephemeral)
                deferred = True
            elif follow_up or deferred:
                await interaction.followup.send(content, embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(content, embed=embed, ephemeral=ephemeral)

        await self.handle_nickname_request(interaction.user, interaction.guild, nickname, reply_func)

    @commands.command(name="nick")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def request_nickname_prefix(self, ctx: commands.Context, *, nickname: str):
        async def reply_func(content=None, ephemeral=True, defer=False, follow_up=False, embed=None):
            if not defer:
                reply_msg = await ctx.reply(content, embed=embed)
                if not embed:
                    await reply_msg.delete(delay=5)

        await self.handle_nickname_request(ctx.author, ctx.guild, nickname, reply_func)

    @commands.command(name="reset", aliases=["clear"])
    async def reset_nickname_prefix(self, ctx: commands.Context):
        if ctx.author.id == ctx.guild.owner_id:
            await ctx.reply("❌ Server Owner's nickname cannot be managed by the bot.")
            return

        try:
            await ctx.author.edit(nick=None, reason="User requested nickname reset via command")
            embed = EmbedHelper.reset_embed()
            await ctx.reply(embed=embed)
        except discord.Forbidden:
            await ctx.reply("❌ I do not have permission to change your nickname. Make sure my role is above yours.")
        except Exception as e:
            hexlogger.error(f"Failed to reset nickname: {e}")

    @app_commands.command(name="help", description="Show the bot's help menu and command list")
    async def help_command(self, interaction: discord.Interaction):
        embed = EmbedHelper.help_embed()
        await interaction.response.send_message(embed=embed)

    @commands.command(name="help")
    async def help_command_prefix(self, ctx: commands.Context):
        embed = EmbedHelper.help_embed()
        await ctx.reply(embed=embed)


    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = await ctx.reply(f"⏳ Please wait **{int(error.retry_after)+1}s** before using this command again.")
            await msg.delete(delay=5)
            try:
                await ctx.message.delete(delay=5)
            except discord.HTTPException:
                pass
            return
        raise error


async def setup(bot):
    await bot.add_cog(NicknameCog(bot))
