import discord
from typing import Optional

class EmbedHelper:
    COLOR_PRIMARY = discord.Color.from_rgb(88, 101, 242)
    COLOR_SUCCESS = discord.Color.from_rgb(46, 204, 113)
    COLOR_ERROR = discord.Color.from_rgb(231, 76, 60)
    COLOR_WARNING = discord.Color.from_rgb(241, 196, 15)
    COLOR_INFO = discord.Color.from_rgb(52, 152, 219)
    
    @staticmethod
    def request_embed(member: discord.Member, requested_nickname: str, sanitized_nickname: str) -> discord.Embed:
        embed = discord.Embed(
            title="📥 Nickname Change Request",
            color=EmbedHelper.COLOR_PRIMARY,
            description="A new nickname change request has been submitted."
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Current Name/Nickname", value=f"`{member.display_name}`", inline=True)
        embed.add_field(name="Requested Nickname", value=f"`{requested_nickname}`", inline=True)
        
        if requested_nickname != sanitized_nickname:
            embed.add_field(name="⚠️ Sanitized Version", value=f"`{sanitized_nickname}`\n*(Will be applied if approved due to active filters)*", inline=False)
            
        embed.set_footer(text=f"Requested by {member.name}", icon_url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        return embed
        
    @staticmethod
    def approved_embed(member: discord.Member, new_nickname: str, approver: str) -> discord.Embed:
        embed = discord.Embed(
            title="✅ Nickname Request Approved",
            color=EmbedHelper.COLOR_SUCCESS,
            description=f"{member.mention}'s nickname request has been approved."
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="New Nickname", value=f"`{new_nickname}`", inline=True)
        embed.add_field(name="Approved By", value=approver, inline=False)
        embed.set_footer(text=f"User: {member.name}", icon_url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def rejected_embed(member: discord.Member, requested_nickname: str, rejecter: str) -> discord.Embed:
        embed = discord.Embed(
            title="❌ Nickname Request Rejected",
            color=EmbedHelper.COLOR_ERROR,
            description=f"{member.mention}'s nickname request has been rejected."
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Requested Nickname", value=f"`{requested_nickname}`", inline=True)
        embed.add_field(name="Rejected By", value=rejecter, inline=False)
        embed.set_footer(text=f"User: {member.name}", icon_url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def auto_sanitized_embed(member: discord.Member, old_name: str, new_nickname: str, reason: str) -> discord.Embed:
        embed = discord.Embed(
            title="🛡️ Name Auto-Sanitized",
            color=EmbedHelper.COLOR_WARNING,
            description=f"Automatically updated {member.mention}'s nickname due to forbidden symbols/formatting."
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Old Name", value=f"`{old_name}`", inline=True)
        embed.add_field(name="New Nickname", value=f"`{new_nickname}`", inline=True)
        embed.add_field(name="Applied Filters", value=reason, inline=False)
        embed.set_footer(text=f"User: {member.name}", icon_url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def status_embed(guild_name: str, config: dict, log_channel: Optional[discord.TextChannel], request_channel: Optional[discord.TextChannel]) -> discord.Embed:
        embed = discord.Embed(
            title=f"⚙️ Nickname Bot Config - {guild_name}",
            color=EmbedHelper.COLOR_INFO,
            description="Current server configuration for nickname filtering and approval system."
        )
        
        log_val = log_channel.mention if log_channel else "🔴 *Not Configured*"
        req_val = request_channel.mention if request_channel else "🔴 *Not Configured*"
        auto_approve_val = "🟢 **Enabled**" if config.get("auto_approve", False) else "🔴 **Disabled (Manual Review)**"
        sanitize_val = "🟢 **Enabled**" if config.get("sanitize_enabled", True) else "🔴 **Disabled**"
        strict_ascii_val = "🟢 **Enabled (Only ASCII allowed)**" if config.get("strict_ascii", False) else "🔴 **Disabled**"
        block_leading_val = "🟢 **Enabled (No prefix symbols)**" if config.get("block_leading_symbol", True) else "🔴 **Disabled**"
        auto_dehoist_val = "🟢 **Enabled (Remove hoist symbols)**" if config.get("auto_dehoist", True) else "🔴 **Disabled**"
        
        embed.add_field(name="Setup Log Channel", value=log_val, inline=True)
        embed.add_field(name="Setup Nickname Channel", value=req_val, inline=True)
        embed.add_field(name="Auto-Approve System", value=auto_approve_val, inline=False)
        embed.add_field(name="Global Sanitization", value=sanitize_val, inline=True)
        embed.add_field(name="Strict ASCII", value=strict_ascii_val, inline=True)
        embed.add_field(name="Block Leading Symbols", value=block_leading_val, inline=True)
        embed.add_field(name="Auto Dehoist", value=auto_dehoist_val, inline=True)
        
        embed.set_footer(text="Manage settings using config commands")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def reset_embed() -> discord.Embed:
        embed = discord.Embed(
            title="✅ Auto-Approved",
            color=EmbedHelper.COLOR_SUCCESS,
            description="Nickname reset to default\n\n🔄 **Need to Reset?**\nSend `reset` or `clear` message in this channel"
        )
        embed.set_footer(text="Operation completed successfully")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def help_embed() -> discord.Embed:
        embed = discord.Embed(
            title="📋 Nickname Bot Help Menu",
            color=EmbedHelper.COLOR_PRIMARY,
            description="Complete guide on how to configure and use the Nickname & Name Sanitizer Bot."
        )
        embed.add_field(
            name="📖 How to Use",
            value=(
                "1. **Admin Setup:** Set up your logs channel and nickname request channel first.\n"
                "2. **Name Requests:** Users can submit nickname requests. If auto-approve is active, the name applies instantly. Otherwise, admins must approve/reject via the request channel panel.\n"
                "3. **Direct Text Requests:** In the designated nickname request channel, users can request names by simply typing them directly into the channel (without typing commands)."
            ),
            inline=False
        )
        embed.add_field(
            name="👤 User Commands",
            value=(
                "• `/request_nickname [desired_nickname]` or `.nick [desired_nickname]` — Request a nickname change.\n"
                "• `.reset` or `.clear` — Clear your guild nickname (resets to default).\n"
                "• Typing `reset` or `clear` in the nickname requests channel also resets your name."
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "• `/logs channel [channel]` or `.logs channel [channel]` — Set logging channel.\n"
                "• `/nickname channel [channel]` or `.nickname channel [channel]` — Set request/reset channel.\n"
                "• `/setup auto_approve [true/false]` or `.setup auto_approve [on/off]` — Toggle auto-approvals.\n"
                "• `/setup filter` or `.setup filter` — Configure symbol filtering options.\n"
                "• `/setup status` or `.setup status` — View configuration details."
            ),
            inline=False
        )
        embed.set_footer(text="Nickname & Name Sanitizer System")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def dm_approved_embed(guild_name: str, new_nickname: str) -> discord.Embed:
        embed = discord.Embed(
            title="✅ Nickname Request Approved",
            color=EmbedHelper.COLOR_SUCCESS,
            description=f"Your nickname request in **{guild_name}** has been approved!"
        )
        embed.add_field(name="New Nickname", value=f"`{new_nickname}`", inline=False)
        embed.set_footer(text=guild_name)
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def dm_rejected_embed(guild_name: str, requested_nickname: str) -> discord.Embed:
        embed = discord.Embed(
            title="❌ Nickname Request Rejected",
            color=EmbedHelper.COLOR_ERROR,
            description=f"Your nickname request in **{guild_name}** has been rejected."
        )
        embed.add_field(name="Requested Nickname", value=f"`{requested_nickname}`", inline=False)
        embed.set_footer(text=guild_name)
        embed.timestamp = discord.utils.utcnow()
        return embed
